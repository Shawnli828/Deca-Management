import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class AppContext:
    database_url: Callable[[], str]
    db_path: Callable[[], Path]
    using_postgres_impl: Callable[[str], bool]
    db_placeholder_impl: Callable[[str], str]
    connect_db_impl: Callable[[str, Path], object]
    init_relational_schema_impl: Callable[[object, bool, str], None]

    def __post_init__(self):
        object.__setattr__(self, "_schema_init_lock", threading.Lock())
        object.__setattr__(self, "_schema_initialized_for", "")

    def using_postgres(self):
        return self.using_postgres_impl(self.database_url())

    def db_placeholder(self):
        return self.db_placeholder_impl(self.database_url())

    def connect_db(self):
        return self.connect_db_impl(self.database_url(), self.db_path())

    def init_relational_schema(self, conn):
        schema_key = self.database_url() or str(self.db_path())
        if self._schema_initialized_for == schema_key:
            return
        with self._schema_init_lock:
            if self._schema_initialized_for == schema_key:
                return
            self.init_relational_schema_impl(conn, self.using_postgres(), self.db_placeholder())
            object.__setattr__(self, "_schema_initialized_for", schema_key)

    def reset_schema_init_cache(self):
        object.__setattr__(self, "_schema_initialized_for", "")
