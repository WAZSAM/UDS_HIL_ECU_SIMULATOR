#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>

// Request a SecurityAccess seed, calculate the matching key, and submit it.
int main() {

    // Open a raw CAN socket for sending and receiving CAN frames.
    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (sock < 0) { perror("Socket creation error"); return 1; }

    // Find the interface index for vcan0 so the socket can bind to it.
    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");
    if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) { perror("IOCTL error"); return 1; }

    // Bind this socket to the virtual CAN interface.
    struct sockaddr_can addr;
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("Bind error"); return 1; }

    // Ask the ECU for a seed using SecurityAccess service 0x27, sub-function 0x01.
    struct can_frame seed_request;
    seed_request.can_id = 0x789;
    seed_request.can_dlc = 3;
    seed_request.data[0] = 0x02;
    seed_request.data[1] = 0x27;
    seed_request.data[2] = 0x01;
    write(sock, &seed_request, sizeof(struct can_frame));

    // Wait for the ECU's positive seed response (service ID 0x67).
    struct can_frame seed_response;
    read(sock, &seed_response, sizeof(struct can_frame));

    // The ECU places the two seed bytes at payload indexes 3 and 4.
    unsigned char seed1 = seed_response.data[3];
    unsigned char seed2 = seed_response.data[4];

    // Calculate the key using the XOR rules implemented by this simulator.
    unsigned char key1 = seed1 ^ 0xA5;
    unsigned char key2 = seed2 ^ 0x5A;

    // Submit the calculated key with SecurityAccess sub-function 0x02.
    struct can_frame key_request;
    key_request.can_id = 0x789;
    key_request.can_dlc = 5;
    key_request.data[0] = 0x04;
    key_request.data[1] = 0x27;
    key_request.data[2] = 0x02;
    key_request.data[3] = key1;
    key_request.data[4] = key2;
    write(sock, &key_request, sizeof(struct can_frame));

    // Read the ECU's response and print its first five payload bytes.
    struct can_frame final_response;
    read(sock, &final_response, sizeof(struct can_frame));
    printf("Final response: %x %x %x %x %x\n",
        final_response.data[0], final_response.data[1], final_response.data[2],
        final_response.data[3], final_response.data[4]);

    // Release the CAN socket before exiting.
    close(sock);
    return 0;
}