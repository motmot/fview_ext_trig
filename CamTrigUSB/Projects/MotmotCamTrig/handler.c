/*
    Interrupt Handler Routines
    Originally By Robert Bailey

*/

/*
Description: This file contains the interrupt handler for the system.
The registered interrupts are called according to their time interval.
The units of time are the overflow of a counter.
*/

#include "handler.h"

#include <avr/interrupt.h>

/* Handler Routine Variables */
volatile unsigned long count[HANDLER_MAX];   /* functions counts */
unsigned long start_count[HANDLER_MAX];      /* functions start counts */
void (*p_handler_func[HANDLER_MAX])(void);   /* handler function pointers */
unsigned char mask[HANDLER_MAX];             /* interrupt mask */

/* Handler Routines */

/*
Function Name: Handler_Init
Description: Initializes routines and timers for the interrupt handler.
Arguments: none
Return Values: none
*/
void Handler_Init(void)
{
    unsigned char lcv;

    for(lcv=0;lcv<HANDLER_MAX;lcv++)    /* Initialize masks to FALSE */
    {
        mask[lcv] = FALSE;
    }
    TIMSK3 |= (1 << TOIE3);
}

/*
Description: The interrupt handler function of the timer3 interrupt.
Arguments: none
Return Values: none
*/
ISR(TIMER3_OVF_vect, ISR_BLOCK)
{
    unsigned char lcv;

    for(lcv=0;lcv<HANDLER_MAX;lcv++)              /* check and act on all vectors */
    {
        if(mask[lcv]==TRUE)                       /* if int enabled check count */
        {
            count[lcv]--;
            if(count[lcv]==0)                     /* if count=0, perform function call and reset */
            {
                count[lcv]=start_count[lcv];
                (*p_handler_func[lcv]) ();
            }
        }
    }
}

/*
Function Name: Reg_Handler
Description: Registers a timed interrupt request with the interrupt handler.
Arguments:
            void* fptr = function pointer to the handler function
            long s_cnt = start count of the timer
            unsigned char priority = priority of the interrupt request
            unsigned char msk = the mask of the interrupt. TRUE/FALSE value
Return Values: none
*/
void Reg_Handler(void* fptr,unsigned long s_cnt,unsigned char priority,unsigned char msk)
{
    mask[priority]=FALSE;               /* disable while modifying vector */
    p_handler_func[priority]=fptr;      /* set function pointer */
    start_count[priority]=s_cnt;        /* set start count */
    count[priority]=s_cnt;              /* set count */
    mask[priority]=msk;                 /* set interrupt mask */
}
