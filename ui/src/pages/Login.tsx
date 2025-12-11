import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";

import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";
import { Loader2 } from "lucide-react";
import { useGetUser } from "@/hooks/useGetUser";

export function Login() {
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  // const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  // const menuRef = useRef(null);
  const location = useLocation();
  const [loggedOutMessage, setLoggedOutMessage] = useState(
    location.state?.message
  );
  const { data: user } = useGetUser(); // TODO

  const { instance, inProgress } = useMsal();

  useEffect(() => {
    if (!user || (user as any).likelyLoggedOut) return;
    navigate("/activity");
  }, [user]);

  const handleLogin = async () => {
    setIsLoggingIn(true);
    console.log("handlelogin", inProgress);
    if (inProgress === "none") {
      instance.loginRedirect(loginRequest);
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);
  // const toggleMobileMenu = () => {
  //   setIsMobileMenuOpen(!isMobileMenuOpen);
  // };

  // Close mobile menu when clicking outside of it
  // useEffect(() => {
  //   const handleClickOutside = (event) => {
  //     if (menuRef.current && !menuRef.current.contains(event.target)) {
  //       setIsMobileMenuOpen(false);
  //     }
  //   };

  //   if (isMobileMenuOpen) {
  //     document.addEventListener("mousedown", handleClickOutside);
  //   } else {
  //     document.removeEventListener("mousedown", handleClickOutside);
  //   }

  //   return () => {
  //     document.removeEventListener("mousedown", handleClickOutside);
  //   };
  // }, [isMobileMenuOpen]);
  return (
    <>
      <header
        className={`w-full py-4 fixed top-0 z-50 px-6 transition-all duration-300 ${
          isScrolled ? "bg-gray-800 shadow-lg" : "bg-transparent"
        }`}
      >
        <nav className="container mx-auto flex justify-between items-center">
          <div className="text-2xl font-semibold text-white tracking-wide m-auto bg-alchemyLogoBg">
            <div className="inline pr-4">
              <img src="/alchemy_logo.png" className="w-[64px] inline" />
            </div>
            <div className="inline text-3xl">Alchemy Law Africa</div>
          </div>
        </nav>
      </header>

      <section className="min-h-screen flex items-center justify-center pt-32 bg-alchemyLogoBg">
        <div className="container mx-auto text-center">
          <h1 className="text-5xl md:text-7xl font-extrabold text-white leading-tight">
            Corporate and commercial legal services with results
          </h1>

          <div className="py-4">
            <Button
              variant="outline"
              className="h-[55px] mt-8 bg-alchemySecondaryLightOrange text-white py-3 px-8 rounded-lg text-lg font-medium shadow-lg transform hover:scale-105 transition duration-300 border-none hover:bg-alchemyPrimaryOrange hover:text-white"
              onClick={handleLogin}
              disabled={isLoggingIn}
            >
              {isLoggingIn && <Loader2 className="animate-spin" />}
              Login
            </Button>
          </div>

          <div className="text-alchemySecondaryLightYellow pt-6">
            {loggedOutMessage}
          </div>
        </div>
      </section>

      <footer className="bg-gray-800 text-gray-400 py-6">
        <div className="container mx-auto text-center">
          <p>&copy; 2025 Alchemy Law Africa. All rights reserved.</p>
        </div>
      </footer>
    </>
  );
}
