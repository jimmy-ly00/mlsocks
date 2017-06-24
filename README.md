# Mid-latency SOCKS5 server

Uses a Stop-And-Go 1-Mix (https://www.freehaven.net/anonbib/cache/stop-and-go.pdf) to delay individual messages from the TCP stream against a truncated exponential distribution for sending and receiving data.

Uses gevent asynchronous I/O and non-blocking sleep to delay messages while handling incoming messages 

## Prerequisite
Linux & Python 2.7
```
pip install gevent
```

## Usage
Runs on localhost 127.0.0.1 and default port 1080:

```
python mlsocks.py
``` 

To test if it's working:
```
curl --socks5 localhost:1080 example.com
```

## References
http://xiaoxia.org/2011/03/29/written-by-python-socks5-server/
