import os
import dotenv

env_path = ".env"
dotenv.set_key(env_path, "TEST_KEY", "TEST_VAL")
print("Done")
