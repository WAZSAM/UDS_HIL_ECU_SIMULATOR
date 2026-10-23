#define _DEFAULT_SOURCE

// Headers for printing, string handling, CAN sockets, and random seed generation.
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <stdlib.h>
#include <time.h>

// Tracks whether the ECU has been unlocked through SecurityAccess.
int ECU_is_locked = 1;

// Stores the two random bytes sent to the tester as the security seed.
unsigned char store_seed = 0;
unsigned char store_seed2 = 0;

// Handles one UDS request and sends the corresponding CAN response.
void check_sid(unsigned char data[], int sock) {
     // Service ID 0x27 is UDS SecurityAccess.
     if (data[1] == 0x27) {
        printf("Security Access \n");

        // Sub-function 0x01 asks the ECU to provide a fresh seed.
        if (data[2] == 0x01){               

            store_seed = rand() % 256;
            store_seed2 = rand() % 256;

            printf("Seed Requested\n");

            // Build a positive seed response (0x67 is the response to 0x27).
            struct can_frame response;
            response.can_id = 0x321;
            response.can_dlc = 5;
            response.data[0] = 0x04;
            response.data[1] = 0x67;
            response.data[2] = 0x01;
            response.data[3] = store_seed;
            response.data[4] = store_seed2;

            write(sock, &response, sizeof(struct can_frame));

        // Sub-function 0x02 submits the key calculated from the seed.
        }else if (data[2] == 0x02)
        {
            printf("Key Submited\n");

            // Check both key bytes against this simulator's XOR-based rule.
            if (data[3] == (store_seed ^ 0xA5) && data[4] == (store_seed2 ^ 0x5A)){

                // A matching key unlocks the ECU and gets a positive response.
                ECU_is_locked = 0;
                struct can_frame response;
                response.can_id = 0x321;
                response.can_dlc = 5;
                response.data[0] = 0x02;
                response.data[1] = 0x67;
                response.data[2] = 0x02;
                response.data[3] = 0x00;
                response.data[4] = 0x00;

                write(sock, &response, sizeof(struct can_frame));

            }
            else{

                // A wrong key gets NRC 0x35 (invalidKey).
                struct can_frame response;
                response.can_id = 0x321;
                response.can_dlc = 5;
                response.data[0] = 0x03;
                response.data[1] = 0x7F;
                response.data[2] = 0x27;
                response.data[3] = 0x35;
                response.data[4] = 0x00;

                write(sock, &response, sizeof(struct can_frame));

            }
        }

        // Any other SecurityAccess sub-function is not handled here.
        else{
            printf("Wrong Sub-Funtion\n");
        }
        
    // Service ID 0x10 is UDS DiagnosticSessionControl.
    } else if (data[1] == 0x10) {
        printf("Session Control \n");

        // Reply with a positive response for the default session.
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
        // The ECU does not implement this service ID.
        printf("Wrong SID \n");
    }
}

int main() {

    // Seed the random-number generator so each run starts with different seeds.
    srand(time(NULL));

    // Create a raw CAN socket used to receive requests and send responses.
    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);

    if (sock < 0) {
        perror("Socket creation error");
        return 1;
    }
    
    // Look up the Linux interface index for the virtual CAN interface.
    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");

    int ioctl_result = ioctl(sock, SIOCGIFINDEX, &ifr);

    if (ioctl_result < 0) {
        perror("IOCTL error");
        return 1;
    }

    // Bind the CAN socket to vcan0 so it can communicate on that bus.
    struct sockaddr_can addr;
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    int bind_result = bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    if (bind_result < 0) {
        perror("Bind error");
        return 1;
    }

    // Keep listening for CAN frames and pass each frame to the UDS handler.
    while(1){
        struct can_frame frame;
        int read_result = read(sock, &frame, sizeof(struct can_frame));
        if (read_result < 0) {
            perror("Read error");
            continue;
        }
        
        // The UDS payload is stored in the CAN frame's data array.
        check_sid(frame.data, sock);
        
        }
    

    // This is reached only if the receive loop ends.
    close(sock);
    return 0;
}
