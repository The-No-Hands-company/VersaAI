add_library(ApiInterface
    ApiInterface.cpp
    ApiInterface.hpp
)
target_include_directories(ApiInterface PRIVATE
    ${CMAKE_SOURCE_DIR}/src/chatbots
    ${CMAKE_SOURCE_DIR}/include
)
target_link_libraries(ApiInterface PRIVATE Chatbots)
