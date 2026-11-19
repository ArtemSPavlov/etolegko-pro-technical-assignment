#!/usr/bin/env python3
"""Замер скорости скачивания: 10 последовательных запросов к одному URL."""
import sys
import time

import requests

REQUESTS_COUNT = 10
TIMEOUT = 30  # секунд на один запрос (connect + read)


def download(session: requests.Session, url: str) -> tuple[float, int]:
    """Один запрос: возвращает (время в секундах, байт скачано)."""
    start = time.perf_counter()
    # identity: без сжатия, считаем объём по реальным байтам тела
    with session.get(url, stream=True, timeout=TIMEOUT,
                     headers={"Accept-Encoding": "identity"}) as response:
        response.raise_for_status()
        size = sum(len(chunk) for chunk in response.iter_content(chunk_size=65536))
    return time.perf_counter() - start, size


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Использование: {sys.argv[0]} <URL>", file=sys.stderr)
        return 2
    url = sys.argv[1]

    with requests.Session() as session:  # keep-alive: TCP+TLS+DNS один раз
        try:
            download(session, url)  # warmup вне замера: TCP slow start
        except requests.RequestException as exc:
            print(f"URL недоступен: {exc}", file=sys.stderr)
            return 1

        times, sizes, failed = [], [], 0
        for _ in range(REQUESTS_COUNT):
            try:
                elapsed, size = download(session, url)
            except requests.RequestException as exc:
                failed += 1
                print(f"Предупреждение: запрос не удался ({exc})", file=sys.stderr)
                continue
            times.append(elapsed)
            sizes.append(size)

    if not times:
        print("Все запросы завершились ошибкой — замер невозможен.", file=sys.stderr)
        return 1

    total_bytes = sum(sizes)
    total_time = sum(times)
    speed_mbps = total_bytes * 8 / total_time / 1_000_000

    if failed:
        print(f"Успешных запросов: {len(times)} из {REQUESTS_COUNT} "
              f"(неудачных: {failed})")
    print(f"Среднее время запроса: {total_time / len(times):.2f} с")
    print(f"Скачано всего: {total_bytes / 1_000_000:.1f} МБ")
    print(f"Скорость скачивания: {speed_mbps:.2f} Мбит/с")
    return 0


if __name__ == "__main__":
    sys.exit(main())
