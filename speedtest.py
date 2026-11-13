#!/usr/bin/env python3
"""Консольный замер скорости скачивания.

Делает N последовательных GET-запросов к указанному URL, полностью
дочитывает тело каждого ответа и выводит среднее время запроса,
общий объём скачанных данных и среднюю скорость скачивания.

Используется только стандартная библиотека Python 3.9+.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

CHUNK_SIZE = 64 * 1024
USER_AGENT = "speedtest-cli-script/1.0"


def fetch(url: str, timeout: float) -> tuple[int, float]:
    """Скачивает URL целиком. Возвращает (кол-во байт, время в секундах)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            # Просим не отдавать закэшированную копию.
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            # Без сжатия, чтобы считать реально переданные байты тела.
            "Accept-Encoding": "identity",
        },
    )
    size = 0
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
    elapsed = time.perf_counter() - start
    return size, elapsed


def human_bytes(n: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{n:.2f} {unit}" if unit != "Б" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.2f} ГБ"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Замер скорости скачивания: N последовательных запросов к URL."
    )
    parser.add_argument("url", help="адрес, к которому делать запросы (например, тяжёлая картинка)")
    parser.add_argument(
        "-n", "--count", type=int, default=10,
        help="количество запросов (по умолчанию 10)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=30.0,
        help="таймаут одного запроса в секундах (по умолчанию 30)",
    )
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count должен быть >= 1")
    if not args.url.startswith(("http://", "https://")):
        parser.error("URL должен начинаться с http:// или https://")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    print(f"URL: {args.url}")
    print(f"Запросов: {args.count}\n")

    sizes, times = [], []
    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(args.url, args.timeout)
        except urllib.error.HTTPError as e:
            print(f"[{i:>2}/{args.count}] ошибка HTTP {e.code}: {e.reason}", file=sys.stderr)
            return 1
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            print(f"[{i:>2}/{args.count}] ошибка соединения: {reason}", file=sys.stderr)
            return 1
        sizes.append(size)
        times.append(elapsed)
        speed = size * 8 / elapsed / 1_000_000 if elapsed > 0 else 0.0
        print(f"[{i:>2}/{args.count}] {human_bytes(size):>10}  {elapsed * 1000:9.1f} мс  {speed:8.2f} Мбит/с")

    total_bytes = sum(sizes)
    total_time = sum(times)
    avg_time = total_time / len(times)
    mbit_s = total_bytes * 8 / total_time / 1_000_000 if total_time > 0 else 0.0
    mbyte_s = total_bytes / total_time / 1_000_000 if total_time > 0 else 0.0

    print("\nИтого:")
    print(f"  Среднее время запроса:  {avg_time * 1000:.1f} мс")
    print(f"  Общий объём данных:     {human_bytes(total_bytes)} ({total_bytes} байт)")
    print(f"  Скорость скачивания:    {mbit_s:.2f} Мбит/с ({mbyte_s:.2f} МБ/с)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.", file=sys.stderr)
        sys.exit(130)
