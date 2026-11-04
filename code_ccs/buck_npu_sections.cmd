/* Supplement to the current MATLAB R2025b c28p55x.cmd, FLASH build.
 * Region names verified against the user's actual linker file/map.
 * Add as an extra linker command file; do NOT replace the base linker file.
 * This fixes placement only. SDK NPU driver/initialization are still required.
 */
SECTIONS
{
    .rodata.tvm          : > FLASH_BANK0_SEC0, PAGE = 0, ALIGN(8)
    .bss.noinit.tvm      : > RAMGS_DATA, PAGE = 1, ALIGN(8)
    .bss.noinit.buck_npu : > RAMGS_DATA, PAGE = 1, ALIGN(8)
}
