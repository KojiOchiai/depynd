import os
import pickle
from typing import Type, List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass

from depynd.config import config


@dataclass
class Node():
    filename: str = ""
    children: Optional[List[Type["Node"]]] = None

    @property
    def is_passed(self):
        raise NotImplementedError()

    @property
    def result(self):
        raise NotImplementedError()

    def remove_cache(self, keep_downstream=False):
        raise NotImplementedError()


@dataclass
class Path(Node):
    @property
    def is_passed(self):
        return os.path.exists(self.filename)

    @property
    def result(self):
        if self.is_passed:
            return self.filename
        else:
            raise FileNotFoundError(self.filename)

    def remove_cache(self, keep_downstream=False):
        if keep_downstream:
            return
        if self.children is not None:
            for chaild in self.children:
                chaild.remove_cache(keep_downstream)


class Function(Node):
    def __init__(self, function=lambda x: x, filename: str = '',
                 parents: Optional[List[Type["Node"]]] = None,
                 named_parents: Optional[Dict[str, Type["Node"]]] = None,
                 children: Optional[List[Type["Node"]]] = None):
        super().__init__(filename, children)
        self.function = function
        self.parents = parents
        self.named_parents = named_parents

    @property
    def is_passed(self):
        return os.path.exists(os.path.join(config.cache_directory, self.filename))

    @property
    def result(self):
        if self.is_passed:
            return self.load_cache()
        else:
            return self.run()

    def load_cache(self):
        with open(os.path.join(config.cache_directory, self.filename), 'rb') as f:
            result = pickle.load(f)
        return result

    def run(self, keep_downstream=False):
        print('{} run'.format(os.path.splitext(self.filename)[0]))
        config.prepare()
        self.remove_cache(keep_downstream)
        args = [p.result for p in self.parents]
        kargs = {k: p.result for k, p in self.named_parents.items()}
        result = self(*args, **kargs)
        with open(os.path.join(config.cache_directory, self.filename), 'wb') as f:
            pickle.dump(result, f)
        return result

    def __call__(self, *args, **kargs):
        return self.function(*args, **kargs)

    @property
    def parents(self):
        return self._parents

    @parents.setter
    def parents(self, parents):
        self._parents = parents
        for p in self.parents:
            if p.children is not None:
                p.children.append(self)
            else:
                p.children = [self]

    @property
    def named_parents(self):
        return self._named_parents

    @named_parents.setter
    def named_parents(self, named_parents):
        self._named_parents = named_parents
        for p in self.named_parents.values():
            if p.children is not None:
                p.children.append(self)
            else:
                p.children = [self]

    def remove_cache(self, keep_downstream=False):
        if self.is_passed:
            os.remove(os.path.join(config.cache_directory, self.filename))
        if keep_downstream:
            return
        if self.children is not None:
            for chaild in self.children:
                chaild.remove_cache(keep_downstream)


def require(*parents: Tuple[Node], **named_parents: Dict[str, Node]) -> Callable[[Callable], Node]:
    def decorator(function):
        return Function(filename=function.__name__ + '.pickle',
                        function=function,
                        parents=list(parents),
                        named_parents=named_parents)
    return decorator
