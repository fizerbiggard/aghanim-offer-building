#!/usr/bin/env python3
"""Проверка локального конфига и запуск видимого тестового скрипта.

route   [--config config.json] [--run-test] [--timeout 60]
route   --publish OWNER/REPO --snapshot hub.json [--dir data]
verdict exit 0 ok | 2 config | 4 checks | 5 test | 124 timeout
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KNOWN_KEYS = {"hub", "country", "locale", "checks", "test_script", "publish_repo"}
CHECK_KEYS = {"paths", "min_gb", "env"}


class ConfigError(Exception):
    pass


def load_config(path):
    path = Path(path)
    if not path.is_file():
        raise ConfigError("нет файла %s" % path)
    try:
        data = json.loads(path.read_text("utf-8"))
    except ValueError as error:
        raise ConfigError("не JSON: %s" % error)
    if not isinstance(data, dict):
        raise ConfigError("ожидался объект JSON")

    unknown = set(data) - KNOWN_KEYS
    if unknown:
        raise ConfigError("unknown key: " + ", ".join(sorted(unknown)))

    checks = data.get("checks", {})
    if not isinstance(checks, dict):
        raise ConfigError("checks должен быть объектом")
    unknown = set(checks) - CHECK_KEYS
    if unknown:
        raise ConfigError("checks: unknown key " + ", ".join(sorted(unknown)))
    for key in ("paths", "env"):
        value = checks.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ConfigError("checks.%s должен быть списком строк" % key)
    if "min_gb" in checks and not isinstance(checks["min_gb"], (int, float)):
        raise ConfigError("checks.min_gb должен быть числом")

    script = data.get("test_script")
    if script is not None and not isinstance(script, str):
        raise ConfigError("test_script должен быть строкой")
    return data, path.resolve().parent


def run_checks(config, root):
    checks = config.get("checks", {})
    results = []
    for rel in checks.get("paths", []):
        results.append(("path %s" % rel, (root / rel).exists()))
    if "min_gb" in checks:
        free = shutil.disk_usage(str(root)).free / 1024 ** 3
        results.append(("free %.2f GiB >= %s" % (free, checks["min_gb"]),
                        free >= checks["min_gb"]))
    for name in checks.get("env", []):
        results.append(("env %s" % name, name in os.environ))
    return results


def run_test(config, root, timeout):
    rel = config.get("test_script")
    if not rel:
        print("test     в конфиге нет test_script — пропускаю")
        return 0
    script = (root / rel).resolve()
    if not script.is_file():
        print("test     нет файла %s" % script)
        return 2
    print("test     %s  %s  timeout %ss" % (sys.executable, script, timeout))
    try:
        done = subprocess.run([sys.executable, str(script)], cwd=str(script.parent),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("test     убит по таймауту")
        return 124
    if done.stdout.strip():
        print(done.stdout.rstrip())
    if done.stderr.strip():
        print(done.stderr.rstrip(), file=sys.stderr)
    print("test     exit %s" % done.returncode)
    return 0 if done.returncode == 0 else 5


def repo_token():
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name].strip()
    path = Path.home() / ".aghanim-token"
    if path.is_file():
        return path.read_text("utf-8").strip()
    return ""


def publish(repo, snapshot, folder):
    if "/" not in repo:
        print("нужно OWNER/REPO")
        return 2
    path = Path(snapshot)
    if not path.is_file():
        print("нет файла снимка: %s" % path)
        return 2
    token = repo_token()
    if not token:
        print("нужен GITHUB_TOKEN с правом Contents: Read and write")
        return 2

    data = path.read_bytes()
    name = "hub_%s.json" % __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    url = "https://api.github.com/repos/%s/contents/%s/%s" % (
        repo, urllib.parse.quote(folder.strip("/"), safe="/"), name)
    body = json.dumps({
        "message": "snapshot %s" % name,
        "content": base64.b64encode(data).decode("ascii"),
    }).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="PUT", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "hub-check",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as error:
        print("HTTP %s: %s" % (error.code, error.read()[:200].decode("utf-8", "replace")))
        return 2
    except OSError as error:
        print("сеть: %s" % error)
        return 2
    print("опубликовано: https://github.com/%s/blob/main/%s/%s" % (repo, folder.strip("/"), name))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="Проверка локального конфига скилла.")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--run-test", action="store_true", help="запустить test_script из конфига")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--publish", nargs="?", const="", default=None, metavar="OWNER/REPO",
                        help="залить снимок в репозиторий; без значения — publish_repo из конфига")
    parser.add_argument("--snapshot", metavar="FILE", help="файл снимка для --publish")
    parser.add_argument("--dir", default="data", help="папка в репозитории (по умолчанию data)")
    args = parser.parse_args(argv)

    try:
        config, root = load_config(args.config)
    except ConfigError as error:
        print("config   %s" % error)
        return 2

    if args.publish is not None or args.snapshot:
        repo = args.publish or config.get("publish_repo") or ""
        if not repo:
            print("config   укажи OWNER/REPO или publish_repo в конфиге")
            return 2
        return publish(repo, args.snapshot or "snapshot/hub.json", args.dir)

    print("config   %s" % Path(args.config).resolve())
    results = run_checks(config, root)
    for label, ok in results:
        print("  %s %s" % ("ok  " if ok else "FAIL", label))
    if not all(ok for _, ok in results):
        return 4

    if args.run_test:
        return run_test(config, root, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
