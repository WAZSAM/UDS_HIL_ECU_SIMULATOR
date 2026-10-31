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

// Counter for failed key submission attempts
int failed_attempts = 0; 

// Timestamp until which the ECU is locked out due to too many failed attempts
time_t lockout_until = 0; 

// Counts the number of failed attempts within the lockout period
int lockout_count = 0; 

// Stores the two random bytes sent to the tester as the security seed.
unsigned char store_seed = 0;
unsigned char store_seed2 = 0;

// Handles one UDS request and sends the corresponding CAN response.
void check_sid(unsigned char data[], int sock) {
     // Service ID 0x27 is UDS SecurityAccess.

    time_t current_time = time(NULL);

     if (data[1] == 0x27) {
        printf("Security Access \n");

        if (current_time < lockout_until) {
            printf("ECU is locked out due to too many failed attempts. Please wait.\n");
            struct can_frame response;
            response.can_id = 0x321;
            response.can_dlc = 5;
            response.data[0] = 0x03;
            response.data[1] = 0x7F;
            response.data[2] = 0x27;
            response.data[3] = 0x37;
            response.data[4] = 0x00;

            write(sock, &response, sizeof(struct can_frame));
            return;
        }

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
                failed_attempts = 0;
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

                failed_attempts++; // Increment the failed attempts counter
                if (failed_attempts >= 3 ) {
                    lockout_until = time(NULL) + (10 << lockout_count); // Lockout duration increases exponentially
                    failed_attempts = 0;
                    lockout_count++; // Increase the lockout count for the next time 
                    printf("Lockout #%d triggered, duration now %d seconds\n", lockout_count, 10 << lockout_count);  
                }

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

    } else if (data[1] == 0x22) {
        printf("Read Data By Identifier \n");

        if (data[2] == 0xF1 && data[3] == 0x90) {
            printf("Read Data By Identifier - VIN \n");

            // Build a positive response for the VIN request.
            struct can_frame response;
            response.can_id = 0x321;
            response.can_dlc = 8;
            response.data[0] = 0x07;
            response.data[1] = 0x62;
            response.data[2] = 0xF1;
            response.data[3] = 0x90;
            response.data[4] = '1';
            response.data[5] = 'H';
            response.data[6] = 'G';
            response.data[7] = 'C';

            write(sock, &response, sizeof(struct can_frame));

        } else if (data[2] == 0xF1 && data[3] == 0x91) {
            printf("Read Data By Identifier - Serial Number \n");

            if (ECU_is_locked) {
                printf("ECU is locked, cannot read Serial Number\n");
                struct can_frame response;
                response.can_id = 0x321;
                response.can_dlc = 5;
                response.data[0] = 0x03;
                response.data[1] = 0x7F;
                response.data[2] = 0x22;
                response.data[3] = 0x33; // NRC 0x33: SecurityAccessDenied
                response.data[4] = 0x00;

                write(sock, &response, sizeof(struct can_frame));
            } else {
                printf("ECU is unlocked, sending Serial Number\n");
                struct can_frame response;
                response.can_id = 0x321;
                response.can_dlc = 8;
                response.data[0] = 0x07;
                response.data[1] = 0x62;
                response.data[2] = 0xF1;
                response.data[3] = 0x91;
                response.data[4] = 'S';
                response.data[5] = 'N';
                response.data[6] = '1';
                response.data[7] = '2';

                write(sock, &response, sizeof(struct can_frame));
            }

        } else {
            printf("Wrong Identifier \n");
            struct can_frame response;
            response.can_id = 0x321;
            response.can_dlc = 5;
            response.data[0] = 0x03;
            response.data[1] = 0x7F;
            response.data[2] = 0x22;
            response.data[3] = 0x31; // NRC 0x31: requestOutOfRange
            response.data[4] = 0x00;

            write(sock, &response, sizeof(struct can_frame));
        }

    } else if (data[1] == 0x19) {
        printf("Read DTC Information \n");

        struct can_frame response;
        response.can_id = 0x321;
        response.can_dlc = 5;
        response.data[0] = 0x03;
        response.data[1] = 0x59;
        response.data[2] = 0x02;
        response.data[3] = 0x00;
        response.data[4] = 0x00;

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
