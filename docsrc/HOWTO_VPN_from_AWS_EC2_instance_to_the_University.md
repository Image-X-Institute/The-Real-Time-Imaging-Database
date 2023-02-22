# Setting up VPN access to the University Network from an EC2 instance

## Connecting with the AWS EC2 instance

To install the VPN client manually, it is necessary to connect with the EC2 instance using SSH. The changes made using SSH are only available till the instance is alive; upon stopping and starting a new instance, the manually made changes are lost.

To connect with the EC2 instance, it is necessary to install the AWS CLI and setup the SSH key pairs for authenticating with the AWS instance.

## Installing VPN Client

The VPN client used to connect with Cisco gateways is not available by default in the EC2 instances and needs to be installed from the EPEL repository. The EPEL repository can be enabled using the following command:

```bash
sudo amazon-linux-extras install epel -y
```
Next, the `openconnect` VPN client should be installed on the instance:
```bash
sudo yum install openconnect vpnc-script
```

## Setting up VPN Slicing

The VPN client, `openconnect` can now be used to connect to the University Cisco gateway using a valid set of username and password. However, doing so would cause the EC2 instance to become a part of the University network and hence would loose its connectivity to the rest of the AWS cloud infrastructure. The EC2 instance would be lost as it cannot be reached via the AWS provided IP address. To avoid this scenario, it is necessary to configure the VPN client to only add a certain subnet of the University to its network configuration.

The `vpn-slice` tool allows easy configuration of the `openconnect` VPN client for splitting the network routes.
```bash
sudo pip3 install https://github.com/dlenski/vpn-slice/archive/master.zip
```
This would install the `vpn-slice` package in the python site-packages and the `vpn-slice` executable in `/usr/local/bin`. To test it the first time, the following command can be executed:
```bash
sudo /usr/local/bin/vpn-slice --self-test
```

## Connecting to the University Network

Now that `vpn-slice` is installed, it can be used to connect with just a specific subnet or host within the University network. The rest of the University network is not directly accessible from the EC2 instance and the EC2 instance does not loose its default gateway or any other routes.

The following command initiates the VPN connection. An appropriate unikey should be used to connect to the network (replace igho9814 with your unikey). The IP address mentioned at the end of the command is that of Trandy, a server within the University network: this can be replaced with any other relevant IP address (or subnet).

```bash
sudo openconnect vpn.sydney.edu.au -u igho9814 -s '/usr/local/bin/vpn-slice 10.65.67.87/31'
```

Invoking the above command would ask the unikey password after which, it should get successfully connected to the University network. The following output from the command shows that the EC2 instance connected with University network using the IP address `10.48.26.102`:

```
POST https://vpn.sydney.edu.au/
Connected to 129.78.42.50:443
SSL negotiation with vpn.sydney.edu.au
Connected to HTTPS on vpn.sydney.edu.au with ciphersuite (TLS1.2)-(ECDHE-RSA-SECP256R1)-(AES-256-GCM)
XML POST enabled
Please enter your username and password.
Password: ********
POST https://vpn.sydney.edu.au/
Got CONNECT response: HTTP/1.1 200 OK
CSTP connected. DPD 30, Keepalive 20
Connected as 10.48.26.102, using SSL, with DTLS in progress
Established DTLS connection (using GnuTLS). Ciphersuite (DTLS0.9)-(DHE-RSA-4294967237)-(AES-256-CBC)-(SHA1).
```

The command would run in the foreground by default, so it can be started as a background process or from within a script.

The following output from `ip addr` shows that the EC2 instance acquired a new network interface named `tun0`, which uses the VPN connection.  

```
$ ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000

...

8: tun0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1300 qdisc pfifo_fast state UNKNOWN group default qlen 500
    link/none
    inet 10.48.26.102/32 scope global tun0
       valid_lft forever preferred_lft forever
    inet6 fe80::7ed5:524b:70d8:1727/64 scope link stable-privacy
       valid_lft forever preferred_lft forever
```

## Configuring Access to the Database

To setup access to the Realtime Imaging database, ensure that the web application configurations list the IP address of `Trandy` as the host for the data base. Apart from this, create a folder with the path `/mnt/uploads` and mount the CIFS filesystem exported from `Trandy` with the same name to this path. If the `cifs-utils` package is not installed already then it would need to installed before mounting the filesystem.

```bash
sudo mount -tcifs //10.65.67.87/uploads /mnt/uploads -ousername=igho9814,uid=$(id -u),gid=$(id -g)
```

# References

* Enabling `epel` repository in Amazon Linux 2 for installing additional packages: https://aws.amazon.com/premiumsupport/knowledge-center/ec2-enable-epel/
* VPN configuration script reference: https://www.infradead.org/openconnect/vpnc-script.html
* Current version of the VPN configuration script: https://gitlab.com/openconnect/vpnc-scripts/raw/master/vpnc-script
* `openconnect` manual: https://www.infradead.org/openconnect/manual.html
*  Wikipedia article on VPN split tunnelling: https://en.wikipedia.org/wiki/Split_tunneling
*  VPN Slice (split tunnelling) script: https://github.com/dlenski/vpn-slice
