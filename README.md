# Mininet-POX assignment

## Manual Test

### Test Connectivity

```
pingallfull
```

**Expected:** all host reachable

### Test learning switch

```
pingallfull
```

**Expected:** all host reachable at a faster time (due to learning)

### Test Fixing

```
h1 ping h4
```

**Expected:** reachable

```
link s1 s2 down
h1 ping h4
link s1 s2 up

link s1 s4 down
h1 ping h8
link s1 s4 up
```

**Expected:** fails for awhile then success (due to timeout/fixing) 
*if it didn't fail for awhile it's probably because its taking the other route so try alt route*

#### alternate route

```
link s1 s4 down
h1 ping h4
link s1 s4 up

link s1 s2 down
h1 ping h8
link s1 s2 up
```

**Expected:**  fails for awhile then success (due to timeout/fixing)



### Test Firewall

```
xterm h1 h4 h6
```

**Expected:**  3 window pop up, do not close them until the end of (4).

```
(h1) python -m SimpleHTTPServer 1001
(h4) wget 10.0.0.1:1001
(h6) wget 10.0.0.1:1001
```

**Expected:**  success

```
(h4) python -m SimpleHTTPServer 2001
(h1) wget 10.0.0.4:2001
(h6) wget 10.0.0.4:2001
```

**Expected:**  success

```
(h6) python -m SimpleHTTPServer 3001
(h4) wget 10.0.0.6:3001
(h1) wget 10.0.0.6:3001
```

**Expected:**  success

#### single ip address

```
xterm h2

(h2) pythom -m SimpleHTTPServer 80
(h1) wget 10.0.0.2:80
(h4) wget 10.0.0.2:80
(h6) wget 10.0.0.2:80
```

**Expected:**  fails (due to firewall)

```
(h1) python -m SimpleHTTPServer 1001
(h4) python -m SimpleHTTPServer 2001
(h6) python -m SimpleHTTPServer 3001
(h2) wget 10.0.0.1:1001
(h2) wget 10.0.0.4:2001
(h2) wget 10.0.0.6:3001
```

**Expected:** fails (due to firewall)
*close h2 window*

#### single ip address with port

````
xterm h7

(h7) python -m SimpleHTTPServer 1001
(h1) wget 10.0.0.7:1001
(h4) wget 10.0.0.7:1001
(h6) wget 10.0.0.7:1001
````

**Expected:** fails (due to firewall)

```
(h7) python -m SimpleHTTPServer 1002
(h1) wget 10.0.0.7:1002
(h4) wget 10.0.0.7:1002
(h6) wget 10.0.0.7:1002
```

**Expected:** success

```
(h1) python -m SimpleHTTPServer 1001
(h4) python -m SimpleHTTPServer 1001
(h6) python -m SimpleHTTPServer 1001
(h7) wget 10.0.0.1:1001
(h7) wget 10.0.0.4:1001
(h7) wget 10.0.0.6:1001 
```

**Expected:** success
*close h7 window*

#### pair ip with port 

```
xterm h5

(h4) python -m SimpleHTTPServer 80
(h5) wget 10.0.0.4:80
```

**Expected:** fails (due to firewall)

```
(h4) python -m SimpleHTTPServer 80
(h1) wget 10.0.0.4:80
```

**Expected:** success

```
(h5) python -m SimpleHTTPServer 80
(h4) wget 10.0.0.5:80
```

**Expected:** success
Close all xterm window

### Test QoS

```
iperf h1 h4
iperf h4 h1
```

**Expected:** 10 > bw > 8 

```
iperf h1 h6
iperf h6 h1
```

**Expected:** 10 > bw > 8

```
iperf h1 h3
iperf h3 h1
```

**Expected:** 5 > bw > 4  

```
iperf h4 h3
iperf h3 h4
```

**Expected:** 5 > bw > 4 

```
iperf h8 h3
iperf h3 h8
```

**Expected:** 3 > bw > 1.5

```
iperf h5 h1
iperf h1 h5
```

**Expected:** 5 > bw > 4 

```
iperf h3 h5
iperf h5 h3
```
**Expected:** 3 > bw > 1.5

```
iperf h5 h7
iperf h7 h5
```
**Expected:** 1 > bw > 0

```
xterm h4 h7 h8

(7) iperf -s
(4) iperf -c 10.0.0.7
(8) iperf -c 10.0.0.7
```

**Expected:** h4 --> 4mb/s, h8 --> 2mb/s