add_executable(bristol-evaluator bristol_circuit_eval_main.cpp)

if (NOT MOTION_BUILD_BOOST_FROM_SOURCES)
    find_package(Boost
            COMPONENTS
            program_options
            REQUIRED)
endif ()

target_link_libraries(bristol-evaluator
        MOTION::motion
        Boost::program_options
        )
