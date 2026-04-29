# logdrift

> Lightweight log aggregation utility that tails and filters structured logs from multiple services in real time.

---

## Installation

```bash
pip install logdrift
```

Or install from source:

```bash
git clone https://github.com/yourname/logdrift.git && cd logdrift && pip install .
```

---

## Usage

Define your services in a `logdrift.yaml` config file:

```yaml
services:
  - name: api
    path: /var/log/api/app.log
  - name: worker
    path: /var/log/worker/app.log

filters:
  level: ["ERROR", "WARNING"]
  fields:
    env: production
```

Then run:

```bash
logdrift tail --config logdrift.yaml
```

You can also filter inline without a config file:

```bash
logdrift tail /var/log/api/app.log --level ERROR --field env=production
```

Output is streamed to stdout in a clean, colorized format with service name, timestamp, log level, and message.

---

## Features

- Tail multiple log files simultaneously
- Filter by log level, field values, or keyword
- Supports JSON and logfmt structured log formats
- Minimal dependencies, fast startup

---

## License

MIT © 2024 [yourname](https://github.com/yourname)