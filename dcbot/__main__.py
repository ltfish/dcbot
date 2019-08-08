

from .logic import populate_db
from .slack_logic import test
from .db import init_db

if __name__ == "__main__":
    # test()
    init_db()
    populate_db()
