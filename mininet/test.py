def run_tests(net):

    def test_pingall(net):
        rtts_results = {}
        info("**** Testing pingall...\n")
        results = net.pingAllFull()
        for hx, hy, rtts in results:
            if hx.name not in rtts_results: rtts_results[hx.name] = {}
            rtts_results[hx.name][hy.name] = rtts[3] 

        results = net.pingAllFull()
        all_slower = True
        for hx, hy, rtts in results:
            if rtts_results[hx.name][hy.name] <= rtts[3]:
                all_slower = False
                info ("****** %s - %s Slower! Before: %s, After %s\n" % (hx.name, hy.name, rtts_results[hx.name][hy.name], rtts[3]))

        if all_slower:
            info ("**** Pingall test success\n")
        else:
            info ("**** Pingall test failure\n")

    def test_specific_tcp_connectivity(net, to_host_num, to_port, from_host=[]):
        to_host_name = "h%d" % to_host_num
        hosts = net.hosts
        to_host = net.get(to_host_name)
        successful_connection = []

        info("****** Testing Connection to %s:%s from " % (to_host_name, to_port))
        for host in hosts:
            if host.name == to_host_name:
                continue
            else:
                info ("%s " % host.name)
                to_host.cmd("nc -l -p %s &" % (to_port, ))
                to_host_pid = int(to_host.cmd("echo $!"))
                host.cmd("echo 'hello' | nc 10.0.0.%s %s &" % (to_host_num, to_port,))
                pid = int(host.cmd("echo $!"))
                time.sleep(0.1)
                isNotKilled = host.cmd("kill", pid)
                if isNotKilled:
                    successful_connection.append(host)
                killed = to_host.cmd("kill", to_host_pid)
        info ("END\n")
        return successful_connection

    def test_tcp_connectivity(net, host, port):
        successes = test_specific_tcp_connectivity(net, host, port)

        connections = []
        for i in range(1,9):
            other_successes = [h.name for h in test_specific_tcp_connectivity(net, i, port)]
            connections.append((i, other_successes, ))

        for connection in connections:
            print ("%s: %s" % connection)

        return successes

    def test_firewall_ip(net):
        info ("**** Testing Firewall with IP\n")
        successes = test_tcp_connectivity(net, 2, 12345)
        if successes:
            info ("**** Firewall with IP failure\n")
        else:
            info ("**** Firewall with IP success\n")

    def test_firewall_ip_port(net):
        info ("**** Testing Firewall with IP and Port\n")
        successes = test_tcp_connectivity(net, 7, 1001)
        if successes:
            info ("**** Firewall with IP and Port failure\n")
        else:
            info ("**** Firewall with IP and Port success\n")

    def test_firewall_src_dst_port(net):
        info ("**** Testing Firewall with Src IP, Dst IP and Port\n")
        successes = test_tcp_connectivity(net, 4, 80)
        if successes:
            info ("**** Firewall with Src IP, Src Dst and Port failure\n")
        else:
            info ("**** Firewall with Src IP, Src Dst and Port success\n")
        


    def test_firewall(net):
        test_firewall_ip(net)
        test_firewall_ip_port(net)
        test_firewall_src_dst_port(net)

    def run(net):
        test_pingall(net)
        test_firewall(net)

    run(net)

run_tests(net)