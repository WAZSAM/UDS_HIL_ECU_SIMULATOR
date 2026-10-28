#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <sys/types.h>

int main() {

    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (sock < 0) { perror("Socket creation error"); return 1; }

    struct ifreq ifr;
    strncpy(ifr.ifr_name, "vcan0", IFNAMSIZ - 1);
    ifr.ifr_name[IFNAMSIZ - 1] = '\0';  // guarantee null-termination regardless of source length
    if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) { perror("IOCTL error"); return 1; }

    struct sockaddr_can addr;
    memset(&addr, 0, sizeof(addr));
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("Bind error"); return 1; }

    // Fix: set a 1-second receive timeout, same role as Python's bus.recv(timeout=1).
    // Without this, read() blocks forever if no frame ever arrives.
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    struct can_frame seed_request;
    memset(&seed_request, 0, sizeof(seed_request));  // zero unused bytes, don't rely on stack garbage
    seed_request.can_id = 0x789;
    seed_request.can_dlc = 3;
    seed_request.data[0] = 0x02;
    seed_request.data[1] = 0x27;
    seed_request.data[2] = 0x01;

    if (write(sock, &seed_request, sizeof(struct can_frame)) != sizeof(struct can_frame)) {
        perror("Write error (seed request)");
        close(sock);
        return 1;
    }

    struct can_frame seed_response;
    ssize_t n = read(sock, &seed_response, sizeof(struct can_frame));
    if (n < 0) {
        // With SO_RCVTIMEO set, a timed-out read() returns -1 with errno EAGAIN/EWOULDBLOCK.
        perror("No seed response (timeout or error)");
        close(sock);
        return 1;
    }

    unsigned char seed1 = seed_response.data[3];
    unsigned char seed2 = seed_response.data[4];

    unsigned char key1 = seed1 ^ 0xA5;
    unsigned char key2 = seed2 ^ 0x5A;

    struct can_frame key_request;
    memset(&key_request, 0, sizeof(key_request));
    key_request.can_id = 0x789;
    key_request.can_dlc = 5;
    key_request.data[0] = 0x04;
    key_request.data[1] = 0x27;
    key_request.data[2] = 0x02;
    key_request.data[3] = key1;
    key_request.data[4] = key2;

    if (write(sock, &key_request, sizeof(struct can_frame)) != sizeof(struct can_frame)) {
        perror("Write error (key request)");
        close(sock);
        return 1;
    }

    struct can_frame final_response;
    n = read(sock, &final_response, sizeof(struct can_frame));
    if (n < 0) {
        perror("No final response (timeout or error)");
        close(sock);
        return 1;
    }

    printf("Final response: %x %x %x %x %x\n",
        final_response.data[0], final_response.data[1], final_response.data[2],
        final_response.data[3], final_response.data[4]);

    close(sock);
    return 0;
}