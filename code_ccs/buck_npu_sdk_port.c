/*
 * 针对当前交付 mod.a 的 TI NPU 运行库适配。下方 TI 原始许可声明完整保留。
 * 重型层加载必须移到可抢占的 main 后台，短 NPU ISR 只登记请求和应答。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
//###########################################################################
//
// FILE:    f28p55x_npu.c
//
// TITLE:   NPU initialization and Support Functions.
//
//###########################################################################
//
//
// 
// C2000Ware v26.02.00.00
//
// Copyright (C) 2024 Texas Instruments Incorporated - http://www.ti.com
//
// Redistribution and use in source and binary forms, with or without 
// modification, are permitted provided that the following conditions 
// are met:
// 
//   Redistributions of source code must retain the above copyright 
//   notice, this list of conditions and the following disclaimer.
// 
//   Redistributions in binary form must reproduce the above copyright
//   notice, this list of conditions and the following disclaimer in the 
//   documentation and/or other materials provided with the   
//   distribution.
// 
//   Neither the name of Texas Instruments Incorporated nor the names of
//   its contributors may be used to endorse or promote products derived
//   from this software without specific prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT 
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
// $
//###########################################################################

//
// Includes
//
#include <stdbool.h>
#include <stdint.h>
#include "driverlib.h"
#include "buck_npu.h"
#include "buck_npu_platform.h"

//
// Defines
//
#define NPU_O_CTL5      0x20U    // Control Register 5 Offset
#define NPU_O_IMASK     0x08U    // Interrupt Mask Register

#pragma FUNCTION_OPTIONS(NPU_setInstrMem, "--opt_level=3 --opt_for_speed=5")
#pragma FUNCTION_OPTIONS(NPU_setParamMem, "--opt_level=3 --opt_for_speed=5")

// Returns the address of the first ACC register of the NPU module.
inline uint32_t NPU_getAccReg(void)
{
    return (ACC_BASE);
}

// Returns address of first CTL register of NPU module.
inline uint32_t NPU_getCtlReg(void)
{
    return (IPSPECIFIC_BASE + NPU_O_CTL5);
}


// Set the instruction memory of the NPU at the specified offset.
/* C28x 是字寻址架构：这里的偏移、目标地址推进和 32 位源数据配合已与当前库匹配。
 * 不能按通用 ARM 字节寻址直觉修改步长，否则会破坏 NPU 指令。 */
void NPU_setInstrMem(uint32_t byteOffset, uint32_t num, const uint32_t *src)
{
    volatile uint32_t *ins = (uint32_t *) (INSTRUCTION_BASE + byteOffset);

    int count_by_4 = num >> 2;
    int count_by_1 = num & 0x3;

    if (count_by_4 > 0)
    {
        while (count_by_4--)
        {
            * ins    = *src++;
            *(ins+2) = *src++;
            *(ins+4) = *src++;
            *(ins+6) = *src++;
            ins   += 8;       /* C28 16-bit addressable, access NPU memory accordingly */
        }
    }
    if (count_by_1 > 0)
    {
        while (count_by_1--)
        {
            *ins++ = *src++;
            ins++;             /* C28 16-bit addressable, access NPU memory accordingly */
        }
    }
}

// Set the parameter memory of the NPU at the specified offset.
/* 参数搬运同样遵守 C28x 与 NPU 的地址单位约定。
 * 此函数由后台层处理调用，可被控制中断抢占，不放入控制环路。 */
void NPU_setParamMem(uint32_t byteOffset, uint32_t num, const uint32_t *src)
{
    volatile uint32_t *params = (uint32_t *) (RFDATA_BASE + byteOffset);

    int count_by_4 = num >> 2;
    int count_by_1 = num & 0x3;

    if (count_by_4 > 0)
    {
        while (count_by_4--)
            {
            * params    = *src++;
            *(params+2) = *src++;
            *(params+4) = *src++;
            *(params+6) = *src++;
            params   += 8;           /* C28 16-bit addressable, access NPU memory accordingly */
            }
    }
    if (count_by_1 > 0)
    {
        while (count_by_1--)
        {
            *params++ = *src++;
            params++;           /* C28 16-bit addressable, access NPU memory accordingly */
        }
    }
}

/* Adapter is pinned to the delivered H15 mod.a SHA256:
 * 56d8660cec6873ac48e7a9529bd1d3523d74d0c35c7d466510aa187ad8ca0457.
 * Disassembly verifies the public interrupt wrapper only calls this ordinary
 * no-argument Helper (also used by __tvm_main__). Never CALL the __interrupt
 * wrapper as a C function: its return instruction is IRET, not LRETR.
 * Re-audit and run golden vectors when replacing the model library.
 */
extern __interrupt void tvmgen_default_IRQHandler(void);
extern void tvmgen_default_IRQHandlerHelper(void);
#define BUCK_NPU_PIEIER (PIECTRL_BASE + PIE_O_IER9)
#define BUCK_NPU_PIE_MASK 0x8000U /* INT_NPU = PIE group 9, channel 16 */

volatile uint16_t buck_npu_irq_pending;
volatile uint32_t buck_npu_irq_count, buck_npu_irq_serviced;
volatile uint32_t buck_npu_irq_overrun, buck_npu_irq_context_errors;
volatile uint32_t buck_npu_irq_binding_errors;
volatile uint32_t buck_npu_irq_unexpected;
static uint16_t buck_npu_irq_registered;

#pragma FUNCTION_OPTIONS(buck_npu_short_isr, "--opt_level=2")
/* 硬件 ISR 只屏蔽本 NPU 通道、置待处理标记并应答 PIE。
 * 不在关中断上下文执行模型 helper 或批量复制权重，避免占满控制时间。 */
__interrupt void buck_npu_short_isr(void)
{
    /* Mask ONLY NPU delivery while main claims this event. Leave other PIE9
     * clients and the control ADC (PIE10.4) enabled. Do not clear PIEIFR: a
     * subsequent layer completion must remain latched until service returns.
     * Avoid Interrupt_disable(INT_NPU), which also clears CPU IFR9. */
    HWREGH(BUCK_NPU_PIEIER) &= (uint16_t)~BUCK_NPU_PIE_MASK;
    if (buck_npu_irq_pending) ++buck_npu_irq_overrun;
    buck_npu_irq_pending=1U;
    ++buck_npu_irq_count;
    HWREGH(PIECTRL_BASE + PIE_O_ACK)=INTERRUPT_ACK_GROUP9;
}

/* main 后台处理模型层推进。调用普通 IRQHandlerHelper，而非 __interrupt 包装函数。
 * 两者返回指令/调用约定不同，不能互换；更换模型库时必须重新核对该接口。 */
void buck_npu_deferred_service(void)
{
    bool wasDisabled;
    if (!buck_npu_irq_pending) return;
    wasDisabled=Interrupt_disableGlobal();
    if (wasDisabled) {
        /* This function must NOT silently re-enable an ISR caller. */
        ++buck_npu_irq_context_errors;
        return;
    }
    buck_npu_irq_pending=0U;
    if (!buck_npu_busy) {
        /* Never advance uninitialized/finished model state on a stray event.
         * Keep only the NPU source masked; control remains interruptible. */
        ++buck_npu_irq_unexpected;
        buck_npu_fault=6U;
        Interrupt_enableGlobal();
        return;
    }
    Interrupt_enableGlobal();
    /* Potentially long parameter/instruction uploads and output unpack now
     * execute with INTM clear. ADC/control can preempt every layer upload.
     * NPU's PIE bit remains masked, so its helper cannot be re-entered. */
    tvmgen_default_IRQHandlerHelper();
    ++buck_npu_irq_serviced;
    /* Do not clear PIEIFR9. A fast next layer may already be complete.
     * The pending interrupt is delivered when this individual bit is set. */
    HWREGH(BUCK_NPU_PIEIER) |= BUCK_NPU_PIE_MASK;
}

// The generated runtime repeats registration for every inference.
/* 运行库可能重复注册，只有首次注册才配置硬件向量。
 * 防止每次推理重设中断状态而丢失进行中的请求。 */
void NPU_setInterruptHandler(void (*handler)(void))
{
    bool wasDisabled;
    if (handler != &tvmgen_default_IRQHandler) {
        ++buck_npu_irq_binding_errors;
        buck_npu_fault=5U;
        return;
    }
    if (buck_npu_irq_registered) return;
    wasDisabled=Interrupt_disableGlobal();
    Interrupt_register(INT_NPU, &buck_npu_short_isr);
    buck_npu_irq_registered=1U;
    Interrupt_enable(INT_NPU);
    if (!wasDisabled) Interrupt_enableGlobal();
}

// Enables the interrupt for the NPU.
void NPU_enableInterrupt(void)
{
    HWREG(IPSTANDARD_BASE + NPU_O_IMASK) |= 0x1;
}

// Clears the interrupt ACK for the NPU.
void NPU_clearInterruptACK(void)
{
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}
