

            document.addEventListener(
                "DOMContentLoaded",
                function () {


                    const menuBtn =
                        document.getElementById(
                            "doctorMobileMenuBtn"
                        );


                    const sidebar =
                        document.getElementById(
                            "doctorSidebar"
                        );


                    const overlay =
                        document.getElementById(
                            "doctorSidebarOverlay"
                        );


                    if (
                        !menuBtn ||
                        !sidebar ||
                        !overlay
                    ) {
                        return;
                    }


                    /* =====================================
                    OPEN / CLOSE SIDEBAR
                    ===================================== */

                    menuBtn.addEventListener(
                        "click",
                        function () {

                            const isOpen =
                                sidebar.classList.contains(
                                    "open"
                                );


                            if (isOpen) {

                                sidebar.classList.remove(
                                    "open"
                                );

                                overlay.classList.remove(
                                    "active"
                                );

                                menuBtn.setAttribute(
                                    "aria-expanded",
                                    "false"
                                );

                            } else {

                                sidebar.classList.add(
                                    "open"
                                );

                                overlay.classList.add(
                                    "active"
                                );

                                menuBtn.setAttribute(
                                    "aria-expanded",
                                    "true"
                                );

                            }

                        }
                    );


                    /* =====================================
                    OVERLAY CLOSE
                    ===================================== */

                    overlay.addEventListener(
                        "click",
                        function () {

                            sidebar.classList.remove(
                                "open"
                            );

                            overlay.classList.remove(
                                "active"
                            );

                            menuBtn.setAttribute(
                                "aria-expanded",
                                "false"
                            );

                        }
                    );


                    /* =====================================
                    CLOSE AFTER CLICKING SIDEBAR LINK
                    ===================================== */

                    const sidebarLinks =
                        sidebar.querySelectorAll("a");


                    sidebarLinks.forEach(
                        function (link) {

                            link.addEventListener(
                                "click",
                                function () {

                                    sidebar.classList.remove(
                                        "open"
                                    );

                                    overlay.classList.remove(
                                        "active"
                                    );

                                    menuBtn.setAttribute(
                                        "aria-expanded",
                                        "false"
                                    );

                                }
                            );

                        }
                    );


                    /* =====================================
                    ESCAPE KEY
                    ===================================== */

                    document.addEventListener(
                        "keydown",
                        function (event) {

                            if (
                                event.key === "Escape"
                            ) {

                                sidebar.classList.remove(
                                    "open"
                                );

                                overlay.classList.remove(
                                    "active"
                                );

                                menuBtn.setAttribute(
                                    "aria-expanded",
                                    "false"
                                );

                            }

                        }
                    );


                    /* =====================================
                    DESKTOP RESIZE
                    ===================================== */

                    window.addEventListener(
                        "resize",
                        function () {

                            if (
                                window.innerWidth > 700
                            ) {

                                sidebar.classList.remove(
                                    "open"
                                );

                                overlay.classList.remove(
                                    "active"
                                );

                                menuBtn.setAttribute(
                                    "aria-expanded",
                                    "false"
                                );

                            }

                        }
                    );

                }
            );

        