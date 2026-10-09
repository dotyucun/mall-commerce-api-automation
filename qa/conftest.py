import os

# Framework self-tests do not run cooperative users; avoid patching pytest's runtime.
os.environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"

pytest_plugins = ["pytester"]
