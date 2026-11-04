###########################################################################
## Makefile generated for component 'buck_ADRC_MBD_NPU_24b'. 
## 
## Makefile     : buck_ADRC_MBD_NPU_24b.mk
## Generated on : Tue Nov 03 02:05:17 2026
## Final product: $(RELATIVE_PATH_TO_ANCHOR)/buck_ADRC_MBD_NPU_24b.out
## Product type : executable
## 
###########################################################################

###########################################################################
## MACROS
###########################################################################

# Macro Descriptions:
# PRODUCT_NAME            Name of the system to build
# MAKEFILE                Name of this makefile

PRODUCT_NAME              = buck_ADRC_MBD_NPU_24b
MAKEFILE                  = buck_ADRC_MBD_NPU_24b.mk
MATLAB_ROOT               = D:/Program Files/MATLAB/R2025b
MATLAB_BIN                = D:/Program Files/MATLAB/R2025b/bin
MATLAB_ARCH_BIN           = $(MATLAB_BIN)/win64
START_DIR                 = C:/Users/34109/Desktop/delivery_file/F28P55_v16
SOLVER                    = 
SOLVER_OBJ                = 
CLASSIC_INTERFACE         = 0
TGT_FCN_LIB               = TI C28x
MODEL_HAS_DYNAMICALLY_LOADED_SFCNS = 0
RELATIVE_PATH_TO_ANCHOR   = ..
C_STANDARD_OPTS           = 
CPP_STANDARD_OPTS         = 
EMPTY                     = 
SPACE                     = $(EMPTY) $(EMPTY)
SPACE_TO_QUESTION         = $(subst $(SPACE),?,$1)
ESCAPE_SPACES             = $(subst $(SPACE),\ ,$1)
SUBSTITUTE_ESCAPED_SPACES = $(subst \ ,__<SPACE>__,$1)
ADD_QUOTES                = $(foreach aPath,$1,"$(aPath)")
REVERT_SPACES             = $(subst __<SPACE>__,$(SPACE),$1)
CONVERT_ESCAPED_SPACES_TO_QUOTES = $(call REVERT_SPACES,$(call ADD_QUOTES,$(call SUBSTITUTE_ESCAPED_SPACES,$1)))

###########################################################################
## TOOLCHAIN SPECIFICATIONS
###########################################################################

# Toolchain Name:          Texas Instruments Code Composer Studio - EABI (C2000)
# Supported Version(s):    
# ToolchainInfo Version:   2025b
# Specification Revision:  1.0
# 
#-------------------------------------------
# Macros assumed to be defined elsewhere
#-------------------------------------------

# CCSINSTALLDIR
# CCSSCRIPTINGDIR
# TARGET_LOAD_CMD_ARGS

#-----------
# MACROS
#-----------

TARGET_SCRIPTINGTOOLS_INSTALLDIR = $(CCSSCRIPTINGDIR)
TI_C2000_SHARED_DIR              = $(MATLAB_ROOT)/toolbox/c2b/tic2000_shared
TI_TOOLS                         = $(CCSINSTALLDIR)/bin
TI_INCLUDE                       = $(CCSINSTALLDIR)/include
TI_LIB                           = $(CCSINSTALLDIR)/lib
CCOUTPUTFLAG                     = --output_file=
LDOUTPUTFLAG                     = --output_file=
EXE_FILE_EXT                     = $(PROGRAM_FILE_EXT)
PRODUCT_HEX                      = $(RELATIVE_PATH_TO_ANCHOR)/$(PRODUCT_NAME).hex
PRODUCT_DWO                      = $(RELATIVE_PATH_TO_ANCHOR)/$(PRODUCT_NAME).dwo
PRODUCT_ELF                      = $(RELATIVE_PATH_TO_ANCHOR)/$(PRODUCT_NAME).elf
DOWN_EXE_JS                      = $(TARGET_PKG_INSTALLDIR)/tic2000/CCS_Config/runProgram_generic.js
CCS_CONFIG                       = $(TARGET_PKG_INSTALLDIR)/tic2000/CCS_Config/f28x_generic.ccxml
PRODUCT_DEP                      = $(PRODUCT_NAME).txt
DEPFILE_UPDATE                   = $(TI_C2000_SHARED_DIR)/tools/PostBuildDepedency/win64/DepedencyFileUpdate.ps1
SHELL                            = %SystemRoot%/system32/cmd.exe

TOOLCHAIN_SRCS = 
TOOLCHAIN_INCS = 
TOOLCHAIN_LIBS = 

#------------------------
# BUILD TOOL COMMANDS
#------------------------

# Assembler: C2000 Assembler
AS_PATH = $(TI_TOOLS)
AS = "$(AS_PATH)/cl2000"

# C Compiler: C2000 C Compiler
CC_PATH = $(TI_TOOLS)
CC = "$(CC_PATH)/cl2000"

# Linker: C2000 Linker
LD_PATH = $(TI_TOOLS)
LD = "$(LD_PATH)/cl2000"

# C++ Compiler: C2000 C++ Compiler
CPP_PATH = $(TI_TOOLS)
CPP = "$(CPP_PATH)/cl2000"

# C++ Linker: C2000 C++ Linker
CPP_LD_PATH = $(TI_TOOLS)
CPP_LD = "$(CPP_LD_PATH)/cl2000"

# Archiver: C2000 Archiver
AR_PATH = $(TI_TOOLS)
AR = "$(AR_PATH)/ar2000"

# MEX Tool: MEX Tool
MEX_PATH = $(MATLAB_ARCH_BIN)
MEX = "$(MEX_PATH)/mex"

# Hex Converter: Hex Converter

# Download: Download
DOWNLOAD_PATH = $(TARGET_SCRIPTINGTOOLS_INSTALLDIR)/bin
DOWNLOAD = "$(DOWNLOAD_PATH)/dss.bat"

# Execute: Execute
EXECUTE = $(PRODUCT)

# Builder: GMAKE Utility
MAKE_PATH = %MATLAB%\bin\win64
MAKE = "$(MAKE_PATH)/gmake"


#-------------------------
# Directives/Utilities
#-------------------------

ASDEBUG             = --symdebug:dwarf_version=3
AS_OUTPUT_FLAG      = --output_file=
CDEBUG              = --symdebug:dwarf_version=3
C_OUTPUT_FLAG       = --output_file=
LDDEBUG             =
OUTPUT_FLAG         = --output_file=
CPPDEBUG            = --symdebug:dwarf_version=3
CPP_OUTPUT_FLAG     = --output_file=
CPPLDDEBUG          =
OUTPUT_FLAG         = --output_file=
ARDEBUG             =
STATICLIB_OUTPUT_FLAG =
MEX_DEBUG           = -g
RM                  = @del /F
ECHO                = @echo
MV                  = @move
RUN                 =

#----------------------------------------
# "Faster Builds" Build Configuration
#----------------------------------------

ARFLAGS              = -r
ASFLAGS              = --abi=eabi \
                       -s \
                       -v28 \
                       -ml \
                       $(ASFLAGS_ADDITIONAL)
CFLAGS               = --abi=eabi \
                       --compile_only \
                       --preproc_dependency="$(@:%.obj=%.dep)" --preproc_with_compile  \
                       -I"$(TI_INCLUDE)" \
                       --large_memory_model \
                       --silicon_version=28 \
                       --define="LARGE_MODEL"
CPPFLAGS             =
CPP_LDFLAGS          =
CPP_SHAREDLIB_LDFLAGS  =
DOWNLOAD_FLAGS       = $(TARGET_LOAD_CMD_ARGS) $(PRODUCT)
EXECUTE_FLAGS        =
OBJCOPYFLAGS_HEX     =  -i "$<" -o "$@" -order MS -romwidth 16 -q
LDFLAGS              = --abi=eabi \
                       -z -I$(TI_LIB) \
                       --stack_size=$(STACK_SIZE) --warn_sections \
                       --heap_size=$(HEAP_SIZE) \
                       --reread_libs --rom_model \
                       --priority \
                       -m"$(PRODUCT_NAME).map"
MEX_CPPFLAGS         =
MEX_CPPLDFLAGS       =
MEX_CFLAGS           =
MEX_LDFLAGS          =
MAKE_FLAGS           = -f $(MAKEFILE)
SHAREDLIB_LDFLAGS    =



###########################################################################
## OUTPUT INFO
###########################################################################

PRODUCT = $(RELATIVE_PATH_TO_ANCHOR)/buck_ADRC_MBD_NPU_24b.out
PRODUCT_TYPE = "executable"
BUILD_TYPE = "Top-Level Standalone Executable"

###########################################################################
## INCLUDE PATHS
###########################################################################

INCLUDES_BUILDINFO = -I$(START_DIR) -I$(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/include -ID:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib -I"$(MATLAB_ROOT)/extern/include" -I"$(MATLAB_ROOT)/simulink/include" -I"$(MATLAB_ROOT)/rtw/c/src" -I"$(MATLAB_ROOT)/rtw/c/src/ext_mode/common" -I"$(MATLAB_ROOT)/rtw/c/ert" -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000/inc" -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000_shared/src" -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000_shared/inc" -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/include -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/calibration/hrpwm/f28p55x/include -ID:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib -ID:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/inc -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/headers/include -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common -I"$(MATLAB_ROOT)/toolbox/shared/can/src/scanutil" -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/math/IQmath/c28/include -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/math/CLAmath/c28/include -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000/src" -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000_soc/src/ipclite" -I"$(MATLAB_ROOT)/toolbox/c2b/tic2000_soc/inc/ipclite" -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/include -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/calibration/hrpwm/f28p55x/include -ID:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib -ID:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/inc -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/headers/include -ID:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/math/IQmath/c28/include -ID:/ti/c2000/C2000Ware_26_02_00_00/libraries/math/CLAmath/c28/include

INCLUDES = $(INCLUDES_BUILDINFO)

###########################################################################
## DEFINES
###########################################################################

DEFINES_ = -D__MW_TARGET_USE_HARDWARE_RESOURCES_H__ -DEABI_32BITDOUBLE
DEFINES_BUILD_ARGS = -DCLASSIC_INTERFACE=0 -DALLOCATIONFCN=0 -DTERMFCN=1 -DONESTEPFCN=1 -DMAT_FILE=0 -DMULTI_INSTANCE_CODE=0 -DINTEGER_CODE=0 -DMT=0
DEFINES_CUSTOM = 
DEFINES_OPTS = -DTID01EQ=0
DEFINES_SKIPFORSIL = -DXCP_CUSTOM_PLATFORM -DEXTMODE_DISABLE_ARGS_PROCESSING=1 -DMW_PIL_SCIFIFOLEN=16 -DF2837X_REG_FORMAT -DMW_F28P55X -DSTACK_SIZE=1024 -DRT -DF28P550SJ9 -DCPU1 -DBOOT_FROM_FLASH=1 -DSHIFT_IQMATH_RAMFUNCS -DCPU_RAMLS_PROG_START=0x8000 -DCPU_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_PROG_START=0xA800 -DCLA_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_DATA_START=0x9800 -DCLA_RAMLS_DATA_LENGTH=0x1000
DEFINES_STANDARD = -DMODEL=buck_ADRC_MBD_NPU_24b -DNUMST=1 -DNCSTATES=0 -DHAVESTDIO -DMODEL_HAS_DYNAMICALLY_LOADED_SFCNS=0

DEFINES = $(DEFINES_) $(DEFINES_BUILD_ARGS) $(DEFINES_CUSTOM) $(DEFINES_OPTS) $(DEFINES_SKIPFORSIL) $(DEFINES_STANDARD)

###########################################################################
## SOURCE FILES
###########################################################################

SRCS = $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_csl.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_board.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_adc.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_pwm.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/buck_ADRC_MBD_NPU_24b.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rtGetInf.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rtGetNaN.c $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rt_nonfinite.c $(START_DIR)/buck_npu_sdk_port.c $(START_DIR)/buck_npu_platform.c D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/interrupt.c D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/sysctl.c "$(MATLAB_ROOT)/toolbox/c2b/tic2000/src/c28P55xBoard_Realtime_Support.c" "$(MATLAB_ROOT)/toolbox/c2b/tic2000_shared/src/MW_c28xGlobalInterrupts.c" D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/dma.c D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/adc.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_cputimers.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_defaultisr.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/headers/source/f28p55x_globalvariabledefs.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_piectrl.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_pievect.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_sysctrl.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_usdelay.asm D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_codestartbranch.asm D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_dma.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_gpio.c D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_adc.c "$(MATLAB_ROOT)/toolbox/c2b/tic2000/src/c2000HardwareTimerConfig.c" "$(MATLAB_ROOT)/toolbox/c2b/tic2000_shared/src/MW_c28xGPIO.c" D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/clb.c D:/ti/c2000/C2000Ware_26_02_00_00/libraries/dsp/FPU/c28/source/fpu32/utility/memcpy_fast.asm "$(MATLAB_ROOT)/toolbox/c2b/tic2000/src/c28P55xSchedulerTimer0.c" "$(MATLAB_ROOT)/toolbox/c2b/tic2000_soc/src/ipclite/mw_soc_c2000_ipc.c"

MAIN_SRC = $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/ert_main.c

ALL_SRCS = $(SRCS) $(MAIN_SRC)

###########################################################################
## OBJECTS
###########################################################################

OBJS = MW_c28xx_csl.obj MW_c28xx_board.obj MW_c28xx_adc.obj MW_c28xx_pwm.obj buck_ADRC_MBD_NPU_24b.obj rtGetInf.obj rtGetNaN.obj rt_nonfinite.obj buck_npu_sdk_port.obj buck_npu_platform.obj interrupt.obj sysctl.obj c28P55xBoard_Realtime_Support.obj MW_c28xGlobalInterrupts.obj dma.obj adc.obj f28p55x_cputimers.obj f28p55x_defaultisr.obj f28p55x_globalvariabledefs.obj f28p55x_piectrl.obj f28p55x_pievect.obj f28p55x_sysctrl.obj f28p55x_usdelay.obj f28p55x_codestartbranch.obj f28p55x_dma.obj f28p55x_gpio.obj f28p55x_adc.obj c2000HardwareTimerConfig.obj MW_c28xGPIO.obj clb.obj memcpy_fast.obj c28P55xSchedulerTimer0.obj mw_soc_c2000_ipc.obj

MAIN_OBJ = ert_main.obj

ALL_OBJS = $(OBJS) $(MAIN_OBJ)

###########################################################################
## PREBUILT OBJECT FILES
###########################################################################

PREBUILT_OBJS = 

###########################################################################
## LIBRARIES
###########################################################################

LIBS = $(START_DIR)/mod.a $(START_DIR)/buck_npu_sections.cmd D:/ti/c2000/C2000Ware_26_02_00_00/libraries/math/IQmath/c28/lib/IQmath_fpu32.lib $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000/src/c28P55xPeripherals.cmd $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000/src/c28p55x.cmd C:/Users/34109/Desktop/delivery_file/F28P55_v16/buck_ADRC_MBD_NPU_24b_ert_rtw/ndp_model_io_strict.obj C:/Users/34109/Desktop/delivery_file/F28P55_v16/buck_ADRC_MBD_NPU_24b_ert_rtw/buck_npu_v15_o2.obj C:/Users/34109/Desktop/delivery_file/F28P55_v16/buck_ADRC_MBD_NPU_24b_ert_rtw/buck_load_observer_v15_o2.obj C:/Users/34109/Desktop/delivery_file/F28P55_v16/buck_ADRC_MBD_NPU_24b_ert_rtw/buck_npu_compensation_v15_o2.obj

###########################################################################
## SYSTEM LIBRARIES
###########################################################################

SYSTEM_LIBS = 

###########################################################################
## ADDITIONAL TOOLCHAIN FLAGS
###########################################################################

#---------------
# C Compiler
#---------------

CFLAGS_SKIPFORSIL = -v28 --float_support=fpu32 -ml -DF28P550SJ9 -DCPU1 -DBOOT_FROM_FLASH=1 --tmu_support=tmu1 --fp_mode=relaxed -DSHIFT_IQMATH_RAMFUNCS -DCPU_RAMLS_PROG_START=0x8000 -DCPU_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_PROG_START=0xA800 -DCLA_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_DATA_START=0x9800 -DCLA_RAMLS_DATA_LENGTH=0x1000
CFLAGS_BASIC = $(DEFINES) $(INCLUDES)

CFLAGS += $(CFLAGS_SKIPFORSIL) $(CFLAGS_BASIC)

#-----------------
# C++ Compiler
#-----------------

CPPFLAGS_SKIPFORSIL = -v28 --float_support=fpu32 -ml -DF28P550SJ9 -DCPU1 -DBOOT_FROM_FLASH=1 --tmu_support=tmu1 --fp_mode=relaxed -DSHIFT_IQMATH_RAMFUNCS -DCPU_RAMLS_PROG_START=0x8000 -DCPU_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_PROG_START=0xA800 -DCLA_RAMLS_PROG_LENGTH=0x1800 -DCLA_RAMLS_DATA_START=0x9800 -DCLA_RAMLS_DATA_LENGTH=0x1000
CPPFLAGS_BASIC = $(DEFINES) $(INCLUDES)

CPPFLAGS += $(CPPFLAGS_SKIPFORSIL) $(CPPFLAGS_BASIC)

#---------------
# C++ Linker
#---------------

CPP_LDFLAGS_ = -l"rts2800_fpu32_eabi.lib" --retain="rts2800_fpu32_eabi.lib(.reset)" --retain="f28p55x_codestartbranch.obj(codestart)"
CPP_LDFLAGS_SKIPFORSIL = --define F28P550SJ9 --define CPU1 --define BOOT_FROM_FLASH=1 --define BOOT_USING_BL=0 --define SHIFT_IQMATH_RAMFUNCS --define CPU_RAMLS_PROG_START=0x8000 --define CPU_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_PROG_START=0xA800 --define CLA_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_DATA_START=0x9800 --define CLA_RAMLS_DATA_LENGTH=0x1000

CPP_LDFLAGS += $(CPP_LDFLAGS_) $(CPP_LDFLAGS_SKIPFORSIL)

#------------------------------
# C++ Shared Library Linker
#------------------------------

CPP_SHAREDLIB_LDFLAGS_ = -l"rts2800_fpu32_eabi.lib" --retain="rts2800_fpu32_eabi.lib(.reset)" --retain="f28p55x_codestartbranch.obj(codestart)"
CPP_SHAREDLIB_LDFLAGS_SKIPFORSIL = --define F28P550SJ9 --define CPU1 --define BOOT_FROM_FLASH=1 --define BOOT_USING_BL=0 --define SHIFT_IQMATH_RAMFUNCS --define CPU_RAMLS_PROG_START=0x8000 --define CPU_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_PROG_START=0xA800 --define CLA_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_DATA_START=0x9800 --define CLA_RAMLS_DATA_LENGTH=0x1000

CPP_SHAREDLIB_LDFLAGS += $(CPP_SHAREDLIB_LDFLAGS_) $(CPP_SHAREDLIB_LDFLAGS_SKIPFORSIL)

#-----------
# Linker
#-----------

LDFLAGS_ = -l"rts2800_fpu32_eabi.lib" --retain="rts2800_fpu32_eabi.lib(.reset)" --retain="f28p55x_codestartbranch.obj(codestart)"
LDFLAGS_SKIPFORSIL = --define F28P550SJ9 --define CPU1 --define BOOT_FROM_FLASH=1 --define BOOT_USING_BL=0 --define SHIFT_IQMATH_RAMFUNCS --define CPU_RAMLS_PROG_START=0x8000 --define CPU_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_PROG_START=0xA800 --define CLA_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_DATA_START=0x9800 --define CLA_RAMLS_DATA_LENGTH=0x1000

LDFLAGS += $(LDFLAGS_) $(LDFLAGS_SKIPFORSIL)

#--------------------------
# Shared Library Linker
#--------------------------

SHAREDLIB_LDFLAGS_ = -l"rts2800_fpu32_eabi.lib" --retain="rts2800_fpu32_eabi.lib(.reset)" --retain="f28p55x_codestartbranch.obj(codestart)"
SHAREDLIB_LDFLAGS_SKIPFORSIL = --define F28P550SJ9 --define CPU1 --define BOOT_FROM_FLASH=1 --define BOOT_USING_BL=0 --define SHIFT_IQMATH_RAMFUNCS --define CPU_RAMLS_PROG_START=0x8000 --define CPU_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_PROG_START=0xA800 --define CLA_RAMLS_PROG_LENGTH=0x1800 --define CLA_RAMLS_DATA_START=0x9800 --define CLA_RAMLS_DATA_LENGTH=0x1000

SHAREDLIB_LDFLAGS += $(SHAREDLIB_LDFLAGS_) $(SHAREDLIB_LDFLAGS_SKIPFORSIL)

###########################################################################
## INLINED COMMANDS
###########################################################################


#-------------------------------------------
# Post build updates - DEP, HEX, DWO/ELF
#-------------------------------------------
all :
ifeq ($(DEPRULES),1)
#--------------------------
# Dependency file updates
#--------------------------
postbuild : $(PRODUCT_DEP)

$(PRODUCT_DEP): $(PRODUCT)
	@echo "### Updating dependency files ..."
	PowerShell -ExecutionPolicy Bypass -command "& '$(DEPFILE_UPDATE)'"
	@echo "### Done Updating dependency files ..."
endif

ifeq ($(PRODUCT_TYPE),"executable")
#--------------------------
# ELF to hex converter
#--------------------------
postbuild : $(PRODUCT_HEX)

$(PRODUCT_HEX): $(PRODUCT)
	@echo "### Invoking postbuild tool "Hex Converter" on "$<"..."
	$(CCSINSTALLDIR)/bin/hex2000 $(OBJCOPYFLAGS_HEX)
	@echo "### Done Invoking postbuild tool "Hex Converter" ..."

#--------------------------
# ELF creation
#--------------------------
postbuild : $(PRODUCT)
	@echo "### Creating ELF file from "$<"..."
	copy /Y $(subst /,\,$(PRODUCT)) $(subst /,\,$(PRODUCT_ELF))
	@echo "### Done creating ELF file ..."

endif

#--------------------------
# Dependency based build rule
#--------------------------
ifeq ($(DEPRULES),1) 
ALL_DEPS:=$(patsubst %.obj,%.d,$(ALL_OBJS))
all:
else
ALL_DEPS:=
endif




-include codertarget_assembly_flags.mk
-include ../codertarget_assembly_flags.mk
-include ../../codertarget_assembly_flags.mk
-include $(ALL_DEPS)


###########################################################################
## PHONY TARGETS
###########################################################################

.PHONY : all build buildobj clean info prebuild postbuild download execute


all : build postbuild
	@echo "### Successfully generated all binary outputs."


build : prebuild $(PRODUCT)


buildobj : prebuild $(OBJS) $(PREBUILT_OBJS) $(LIBS)
	@echo "### Successfully generated all binary outputs."


prebuild : 


postbuild : $(PRODUCT)


download : postbuild
	@echo "### Invoking postbuild tool "Download" ..."
	$(DOWNLOAD) $(DOWNLOAD_FLAGS)
	@echo "### Done invoking postbuild tool."


execute : download
	@echo "### Invoking postbuild tool "Execute" ..."
	$(EXECUTE) $(EXECUTE_FLAGS)
	@echo "### Done invoking postbuild tool."


###########################################################################
## FINAL TARGET
###########################################################################

#-------------------------------------------
# Create a standalone executable            
#-------------------------------------------

$(PRODUCT) : $(OBJS) $(PREBUILT_OBJS) $(LIBS) $(MAIN_OBJ)
	@echo "### Creating standalone executable "$(PRODUCT)" ..."
	$(LD) $(LDFLAGS) --output_file=$(PRODUCT) $(OBJS) $(MAIN_OBJ) $(call CONVERT_ESCAPED_SPACES_TO_QUOTES,$(LIBS)) $(SYSTEM_LIBS) $(TOOLCHAIN_LIBS)
	@echo "### Created: $(PRODUCT)"


###########################################################################
## INTERMEDIATE TARGETS
###########################################################################

#---------------------
# SOURCE-TO-OBJECT
#---------------------

%.obj : %.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : %.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : %.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : %.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(RELATIVE_PATH_TO_ANCHOR)/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(RELATIVE_PATH_TO_ANCHOR)/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(RELATIVE_PATH_TO_ANCHOR)/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(RELATIVE_PATH_TO_ANCHOR)/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/rtw/c/src/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/rtw/c/src/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/rtw/c/src/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/rtw/c/src/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/simulink/src/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/simulink/src/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/simulink/src/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/simulink/src/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/toolbox/simulink/blocks/src/%.cla
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/toolbox/simulink/blocks/src/%.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/toolbox/simulink/blocks/src/%.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


%.obj : $(call SPACE_TO_QUESTION,$(MATLAB_ROOT))/toolbox/simulink/blocks/src/%.cpp
	$(CPP) $(CPPFLAGS) --output_file="$@" "$<"


MW_c28xx_csl.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_csl.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


MW_c28xx_board.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_board.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


MW_c28xx_adc.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_adc.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


MW_c28xx_pwm.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/MW_c28xx_pwm.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


buck_ADRC_MBD_NPU_24b.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/buck_ADRC_MBD_NPU_24b.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


ert_main.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/ert_main.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


rtGetInf.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rtGetInf.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


rtGetNaN.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rtGetNaN.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


rt_nonfinite.obj : $(START_DIR)/buck_ADRC_MBD_NPU_24b_ert_rtw/rt_nonfinite.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


buck_npu_sdk_port.obj : $(START_DIR)/buck_npu_sdk_port.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


buck_npu_platform.obj : $(START_DIR)/buck_npu_platform.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


interrupt.obj : D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/interrupt.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


sysctl.obj : D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/sysctl.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


c28P55xBoard_Realtime_Support.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000/src/c28P55xBoard_Realtime_Support.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


MW_c28xGlobalInterrupts.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000_shared/src/MW_c28xGlobalInterrupts.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


dma.obj : D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/dma.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


adc.obj : D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/adc.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_cputimers.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_cputimers.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_defaultisr.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_defaultisr.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_globalvariabledefs.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/headers/source/f28p55x_globalvariabledefs.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_piectrl.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_piectrl.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_pievect.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_pievect.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_sysctrl.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_sysctrl.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_usdelay.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_usdelay.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


f28p55x_codestartbranch.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_codestartbranch.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


f28p55x_dma.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_dma.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_gpio.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_gpio.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


f28p55x_adc.obj : D:/ti/c2000/C2000Ware_26_02_00_00/device_support/f28p55x/common/source/f28p55x_adc.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


c2000HardwareTimerConfig.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000/src/c2000HardwareTimerConfig.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


MW_c28xGPIO.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000_shared/src/MW_c28xGPIO.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


clb.obj : D:/ti/c2000/C2000Ware_26_02_00_00/driverlib/f28p55x/driverlib/clb.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


memcpy_fast.obj : D:/ti/c2000/C2000Ware_26_02_00_00/libraries/dsp/FPU/c28/source/fpu32/utility/memcpy_fast.asm
	$(AS) $(ASFLAGS) --output_file="$@" "$<"


c28P55xSchedulerTimer0.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000/src/c28P55xSchedulerTimer0.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


mw_soc_c2000_ipc.obj : $(call ESCAPE_SPACES,$(MATLAB_ROOT))/toolbox/c2b/tic2000_soc/src/ipclite/mw_soc_c2000_ipc.c
	$(CC) $(CFLAGS) --output_file="$@" "$<"


###########################################################################
## DEPENDENCIES
###########################################################################

$(ALL_OBJS) : rtw_proj.tmw $(MAKEFILE)


###########################################################################
## MISCELLANEOUS TARGETS
###########################################################################

info : 
	@echo "### PRODUCT = $(PRODUCT)"
	@echo "### PRODUCT_TYPE = $(PRODUCT_TYPE)"
	@echo "### BUILD_TYPE = $(BUILD_TYPE)"
	@echo "### INCLUDES = $(INCLUDES)"
	@echo "### DEFINES = $(DEFINES)"
	@echo "### ALL_SRCS = $(ALL_SRCS)"
	@echo "### ALL_OBJS = $(ALL_OBJS)"
	@echo "### LIBS = $(LIBS)"
	@echo "### MODELREF_LIBS = $(MODELREF_LIBS)"
	@echo "### SYSTEM_LIBS = $(SYSTEM_LIBS)"
	@echo "### TOOLCHAIN_LIBS = $(TOOLCHAIN_LIBS)"
	@echo "### ASFLAGS = $(ASFLAGS)"
	@echo "### CFLAGS = $(CFLAGS)"
	@echo "### LDFLAGS = $(LDFLAGS)"
	@echo "### SHAREDLIB_LDFLAGS = $(SHAREDLIB_LDFLAGS)"
	@echo "### CPPFLAGS = $(CPPFLAGS)"
	@echo "### CPP_LDFLAGS = $(CPP_LDFLAGS)"
	@echo "### CPP_SHAREDLIB_LDFLAGS = $(CPP_SHAREDLIB_LDFLAGS)"
	@echo "### ARFLAGS = $(ARFLAGS)"
	@echo "### MEX_CFLAGS = $(MEX_CFLAGS)"
	@echo "### MEX_CPPFLAGS = $(MEX_CPPFLAGS)"
	@echo "### MEX_LDFLAGS = $(MEX_LDFLAGS)"
	@echo "### MEX_CPPLDFLAGS = $(MEX_CPPLDFLAGS)"
	@echo "### OBJCOPYFLAGS_HEX = $(OBJCOPYFLAGS_HEX)"
	@echo "### DOWNLOAD_FLAGS = $(DOWNLOAD_FLAGS)"
	@echo "### EXECUTE_FLAGS = $(EXECUTE_FLAGS)"
	@echo "### MAKE_FLAGS = $(MAKE_FLAGS)"


clean : 
	$(ECHO) "### Deleting all derived files ..."
	$(RM) $(subst /,\,$(PRODUCT))
	$(RM) $(subst /,\,$(ALL_OBJS))
	$(RM) *Object
	$(ECHO) "### Deleted all derived files."


