#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>

int main() {

    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);

    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");
    ioctl(sock, SIOCGIFINDEX, &ifr);


    struct sockaddr_can addr;
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    struct can_frame frame;
    frame.can_id = 0x789;
    frame.can_dlc = 3;
    frame.data[0] = 0x02;
    frame.data[1] = 0x10;
    frame.data[2] = 0x01;

    write(sock, &frame, sizeof(struct can_frame));

    close(sock);
    return 0;
}
