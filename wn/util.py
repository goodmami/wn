"""Wn utility classes."""

from typing import TextIO
import sys


class ProgressHandler:
    """An interface for updating progress in long-running processes.

    Long-running processes in Wn, such as :func:`wn.download` and
    :func:`wn.add`, call to a progress handler object as they go.  The
    default progress handler used by Wn is :class:`ProgressBar`, which
    updates progress by formatting and printing a textual bar to
    stderr. The :class:`ProgressHandler` class may be used directly,
    which does nothing, or users may create their own subclasses for,
    e.g., updating a GUI or some other handler.

    The initialization parameters, except for ``file``, are stored in
    a :attr:`kwargs` member and may be updated after the handler is
    created through the :meth:`set` method. The :meth:`update` method
    is the primary way a counter is updated. The :meth:`flash` method
    is sometimes called for simple messages. When the process is
    complete, the :meth:`close` method is called, optionally with a
    message.

    """

    def __init__(
        self,
        *,
        message: str = '',
        count: int = 0,
        total: int = 0,
        unit: str = '',
        status: str = '',
        file: TextIO = sys.stderr,
    ):
        self.file = file
        self.kwargs = {
            'count': count,
            'total': total,
            'message': message,
            'unit': unit,
            'status': status,
        }

    def update(self, n: int = 1) -> None:
        """Update the counter with the increment value *n*.

        This method should update the ``count`` key of :attr:`kwargs`
        with the increment value *n*. After this, it is expected to
        update some user-facing progress indicator.

        """
        self.kwargs['count'] += n  # type: ignore

    def set(self, **kwargs) -> None:
        """Update progress handler parameters.

        Calling this method also runs :meth:`update` with an increment
        of 0, which causes a refresh of any indicator without changing
        the counter.

        """
        self.kwargs.update(**kwargs)
        self.update(0)

    def flash(self, message: str) -> None:
        """Issue a message unrelated to the current counter.

        This may be useful for multi-stage processes to indicate the
        move to a new stage, or to log unexpected situations.

        """
        pass

    def close(self) -> None:
        """Close the progress handler.

        This might be useful for closing file handles or cleaning up
        resources.

        """
        pass


class ProgressBar(ProgressHandler):
    """A :class:`ProgressHandler` subclass for printing a progress bar.

    Example:
        >>> p = ProgressBar(message='Progress: ', total=10, unit='units')
        >>> p.update(3)
        Progress: [#########                     ] (3/10 units)

    """

    FMT = '\r{message} [{fill:<{width}}] ({count}/{total} {unit}) {status}'

    def update(self, n: int = 1) -> None:
        self.kwargs['count'] += n  # type: ignore
        s = self.format()
        if self.file:
            print('\r\033[K', end='', file=self.file)
            print(s, end='', file=self.file)

    def set(self, **kwargs) -> None:
        self.kwargs.update(**kwargs)
        self.update(0)

    def format(self) -> str:
        _kw = self.kwargs
        width = 30
        total: int = _kw['total']  # type: ignore
        count: int = _kw['count']  # type: ignore

        if total > 0:
            num = min(count, total) * width
            fill = (num // total) * '#'
            part = ((num % total) * 3) // total
            if part:
                fill += '-='[part-1]
        else:
            fill = '-' * width

        return self.FMT.format(fill=fill, width=width, **_kw)

    def flash(self, message: str) -> None:
        print(f'\r\033[K{message}', end='', file=self.file)

    def close(self) -> None:
        print(file=self.file)
