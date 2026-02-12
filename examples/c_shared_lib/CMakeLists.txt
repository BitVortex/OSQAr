cmake_minimum_required(VERSION 3.16)
project(osqar_shared_lib_c LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(OSQAR_COVERAGE "Enable code coverage instrumentation" OFF)

add_library(osqar_shared
    src/osqar_shared.c
)

target_include_directories(osqar_shared PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(osqar_shared PRIVATE -std=c11)

# Only build the test executable when this directory is the top-level project.
# When included via add_subdirectory() from other examples, this avoids target
# name collisions like multiple `junit_tests`.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    add_executable(junit_tests
        tests/test_osqar_shared.c
    )

    target_link_libraries(junit_tests PRIVATE osqar_shared)
    target_compile_options(junit_tests PRIVATE -std=c11)

    if(OSQAR_COVERAGE)
        if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
            foreach(tgt osqar_shared junit_tests)
                target_compile_options(${tgt} PRIVATE -O0 -g --coverage)
                if(COMMAND target_link_options)
                    target_link_options(${tgt} PRIVATE --coverage)
                else()
                    target_link_libraries(${tgt} PRIVATE --coverage)
                endif()
            endforeach()
        endif()
    endif()
endif()
