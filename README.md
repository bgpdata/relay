# Relay

This service provides a robust BGP message relay system that processes and forwards BGP monitoring protocol (BMP) messages. Built with Python and RocksDB, it handles message queuing, database persistence, and real-time message forwarding through Kafka. The service is designed for high-performance data ingestion from [Route Views](https://www.routeviews.org/) and [RIPE NCC RIS](https://ris.ripe.net/).

## Build

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```