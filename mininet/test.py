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
            return True
        else:
            info ("**** Pingall test failure\n")
            return False

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
            return False
        else:
            info ("**** Firewall with IP success\n")
            return True

    def test_firewall_ip_port(net):
        info ("**** Testing Firewall with IP and Port\n")
        successes = test_tcp_connectivity(net, 7, 1001)
        if successes:
            info ("**** Firewall with IP and Port failure\n")
            return False
        else:
            info ("**** Firewall with IP and Port success\n")
            return True

    def test_firewall_src_dst_port(net):
        info ("**** Testing Firewall with Src IP, Dst IP and Port\n")
        successes = test_tcp_connectivity(net, 4, 80)

        if 'h5' not in successes:
            info ("**** Firewall with Src IP, Src Dst and Port success\n")
            return True
        else:
            info ("**** Firewall with Src IP, Src Dst and Port failure\n")
            return False
        


    def test_firewall(net):
        return test_firewall_ip(net) and \
                test_firewall_ip_port(net) and \
                test_firewall_src_dst_port(net)

    def test_service_class_pair(h1, h2, bw1, bw2, lo=0, hi=10):
        n1 = net.get(h1)
        n2 = net.get(h2)
        client, _client = net.iperf([n1, n2])
        server, _server = net.iperf([n2, n1])
        server = float(server.split(" ")[0])
        client = float(client.split(" ")[0])
        return server >= lo * bw1 and server <= hi * bw1 and \
                client >= lo * bw2 and client <= hi * bw2

    def test_premium(net):
        return test_service_class_pair('h1', 'h4', 10, 10, lo=0.8, hi=1) and \
                test_service_class_pair('h1', 'h6', 10, 10, lo=0.8, hi=1) and \
                test_service_class_pair('h6', 'h4', 10, 10, lo=0.8, hi=1)
        
    def test_regular(net):
        return test_service_class_pair("h3", "h8", 5, 10, lo=0.3, hi=0.6)

    def test_free(net):
        
        return test_service_class_pair("h5", "h7", 5, 5, lo=0, hi=0.2)

    def test_service_class(net):
        info ("**** Testing Service Class\n")
        return test_premium(net) and test_regular(net) and test_free(net)

    def run(net):
        if test_service_class(net):
            info ("\n** All Test Passed!\n")
        else: info("\n** Some Test Failed!\n")

    run(net)

run_tests(net)