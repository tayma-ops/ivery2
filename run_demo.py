"""Run a separate, repeatable local demo without changing an existing database."""

import argparse, os, secrets, subprocess, sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8105)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Interactively create an administrator in the isolated demo database",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    local = root / ".local"
    local.mkdir(exist_ok=True)
    secret = local / "django-secret.txt"
    if not secret.exists():
        try:
            with secret.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_urlsafe(64))
        except FileExistsError:
            pass
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_DB_PATH": str(local / "demo.sqlite3"),
            "DJANGO_SECRET_KEY": secret.read_text(encoding="utf-8"),
            "DJANGO_DEBUG": "1",
            "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost,[::1]",
        }
    )
    # The assistant is opt-in; no test/launcher makes a paid provider request.
    for command in [["migrate", "--noinput"], ["seed_demo"]]:
        subprocess.run(
            [sys.executable, "-B", "manage.py", *command], cwd=root, env=env, check=True
        )
    if args.create_admin:
        subprocess.run(
            [sys.executable, "-B", "manage.py", "createsuperuser"],
            cwd=root,
            env=env,
            check=True,
        )
    print("Demo database:", local / "demo.sqlite3", flush=True)
    print(
        "Original db.sqlite3 is unchanged. Create your own account; no default password exists.",
        flush=True,
    )
    if not args.prepare_only:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{args.port}",
                    "--noreload",
                ],
                cwd=root,
                env=env,
                check=True,
            )
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
