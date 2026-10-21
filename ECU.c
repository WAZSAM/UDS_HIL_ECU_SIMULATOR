#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>

void check_sid(unsigned char data[], int sock) {
     if (data[1] == 0x27) {
        printf("Security Access \n");

        struct can_frame response;
        response.can_id = 0x321;
        response.can_dlc = 5;
        response.data[0] = 0x04;
        response.data[1] = 0x67;
        response.data[2] = 0x01;
        response.data[3] = 0x12;
        response.data[4] = 0x34;

        write(sock, &response, sizeof(struct can_frame));

    } else if (data[1] == 0x10) {
        printf("Session Control \n");

        struct can_frame response;
        response.can_id = 0x321;
        response.can_dlc = 7;
        response.data[0] = 0x06;
        response.data[1] = 0x50;
        response.data[2] = 0x01;
        response.data[3] = 0x00;
        response.data[4] = 0x32;
        response.data[5] = 0x01;
        response.data[6] = 0xF4;
    
        write(sock, &response, sizeof(struct can_frame));

    } else {
        printf("Wrong SID \n");
    }
}

int main() {

    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);

    if (sock < 0) {
        perror("Socket creation error");
        return 1;
    }
    
    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");

    int ioctl_result = ioctl(sock, SIOCGIFINDEX, &ifr);

    if (ioctl_result < 0) {
        perror("IOCTL error");
        return 1;
    }

    struct sockaddr_can addr;
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    int bind_result = bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    if (bind_result < 0) {
        perror("Bind error");
        return 1;
    }

    while(1){
        struct can_frame frame;
        int read_result = read(sock, &frame, sizeof(struct can_frame));
        if (read_result < 0) {
            perror("Read error");
            continue;
        }
        
        check_sid(frame.data, sock);
        
        }
    

    close(sock);
    return 0;
}

