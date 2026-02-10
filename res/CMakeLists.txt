# Tested CMake versions:
cmake_minimum_required(VERSION 3.14...3.27)

# Project name, description, language, etc.
project(milestone5
	DESCRIPTION "Milestone 4"
    LANGUAGES CXX)

# Version numbers:
set(VERSION_MAJOR 0)
set(VERSION_MINOR 0)
set(VERSION_PATCH 0)

# Executable(s):
add_executable(milestone5)

# Debug build compiler flags.
set(CMAKE_CXX_FLAGS_DEBUG_INIT "-Wall")

# Release build compiler flags.
set(CMAKE_CXX_FLAGS_RELEASE_INIT "")

# Add source files to target(s).
file(GLOB SRC *.cpp)
target_sources(milestone5 PRIVATE ${SRC})

# Copy necessary directories into build directory, for executable root access.
add_custom_command(TARGET milestone5 PRE_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
		${CMAKE_SOURCE_DIR}/*json $<TARGET_FILE_DIR:milestone5>)
