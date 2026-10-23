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
    if (sock < 0) { perror("Socket creation error"); return 1; }

    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");
    if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) { perror("IOCTL error"); return 1; }

    struct sockaddr_can addr;
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("Bind error"); return 1; }

    // STEP 1: send seed request — client sends SID 0x27, sub-function 0x01
    struct can_frame seed_request;
    seed_request.can_id = 0x789;
    seed_request.can_dlc = 3;
    seed_request.data[0] = 0x02;
    seed_request.data[1] = 0x27;
    seed_request.data[2] = 0x01;
    write(sock, &seed_request, sizeof(struct can_frame));

    // STEP 2: read the ECU's reply (SID 0x67, seed bytes at index 3,4)
    struct can_frame seed_response;
    read(sock, &seed_response, sizeof(struct can_frame));

    // STEP 3: extract the seed from the ECU's actual reply
    unsigned char seed1 = seed_response.data[3];
    unsigned char seed2 = seed_response.data[4];

    // STEP 4: compute the key
    unsigned char key1 = seed1 ^ 0xA5;
    unsigned char key2 = seed2 ^ 0x5A;

    // STEP 5: send key — client sends SID 0x27, sub-function 0x02
    struct can_frame key_request;
    key_request.can_id = 0x789;
    key_request.can_dlc = 5;
    key_request.data[0] = 0x04;
    key_request.data[1] = 0x27;
    key_request.data[2] = 0x02;
    key_request.data[3] = key1;
    key_request.data[4] = key2;
    write(sock, &key_request, sizeof(struct can_frame));

    // STEP 6: read and print the ECU's final verdict
    struct can_frame final_response;
    read(sock, &final_response, sizeof(struct can_frame));
    printf("Final response: %x %x %x %x %x\n",
        final_response.data[0], final_response.data[1], final_response.data[2],
        final_response.data[3], final_response.data[4]);

    close(sock);
    return 0;
}