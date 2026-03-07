/**
 * @file versaai_core.cpp
 * @brief MINIMAL Python bindings for VersaAI C++ Logger
 *
 * This is a minimal working binding that only exposes the Logger.
 * Additional bindings will be added incrementally once this builds successfully.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "VersaAILogger.hpp"

namespace py = pybind11;
using namespace VersaAI;

PYBIND11_MODULE(versaai_core, m) {
    m.doc() = "VersaAI C++ Core - Logger Bindings (Minimal Version)\n\n"
              "This module provides Python access to VersaAI's high-performance C++ logger.";

    // ============================================================================
    // LOGGING
    // ============================================================================

    py::enum_<LogLevel>(m, "LogLevel", "Logging severity levels")
        .value("DEBUG", LogLevel::DEBUG, "Detailed debugging information")
        .value("INFO", LogLevel::INFO, "Informational messages")
        .value("WARNING", LogLevel::WARNING, "Warning messages")
        .value("ERROR", LogLevel::ERROR, "Error messages")
        .value("CRITICAL", LogLevel::CRITICAL, "Critical failures")
        .export_values();

    py::class_<Logger, std::unique_ptr<Logger, py::nodelete>>(m, "Logger",
                                                                "High-performance structured logger (singleton)")
        .def_static("get_instance", &Logger::getInstance,
                   py::return_value_policy::reference,
                   "Get the singleton Logger instance")

        .def("debug",
             [](Logger& self, const std::string& message, const std::string& component) {
                 self.debug(message, component);
             },
             py::arg("message"),
             py::arg("component") = "Python",
             "Log a DEBUG message")

        .def("info",
             [](Logger& self, const std::string& message, const std::string& component) {
                 self.info(message, component);
             },
             py::arg("message"),
             py::arg("component") = "Python",
             "Log an INFO message")

        .def("warning",
             [](Logger& self, const std::string& message, const std::string& component) {
                 self.warning(message, component);
             },
             py::arg("message"),
             py::arg("component") = "Python",
             "Log a WARNING message")

        .def("error",
             [](Logger& self, const std::string& message, const std::string& component) {
                 self.error(message, component);
             },
             py::arg("message"),
             py::arg("component") = "Python",
             "Log an ERROR message")

        .def("critical",
             [](Logger& self, const std::string& message, const std::string& component) {
                 self.critical(message, component);
             },
             py::arg("message"),
             py::arg("component") = "Python",
             "Log a CRITICAL message");

    // ============================================================================
    // VERSION INFO
    // ============================================================================

    m.attr("__version__") = "0.1.0";
    m.attr("__cpp_version__") = "C++23";
    m.attr("__note__") = "Minimal bindings - Logger only. Full bindings coming soon.";
}
