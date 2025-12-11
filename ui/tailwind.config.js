/** @type {import('tailwindcss').Config} */

const plugin = require("tailwindcss/plugin");

module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: "true",
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    // fontWeight: {},
    extend: {
      colors: {
        alchemyLogoBg: "#0c1942",
        alchemyPDFBg: "#161E3E",
        alchemyPrimaryDarkGrey: "#212121",
        alchemyPrimaryOrange: "#EC6D05",
        alchemyPrimaryRed: "#E82A32",
        alchemyPrimaryNavyBlue: "#0A1845",
        alchemyPrimaryGoldenWeb: "#F5B520",
        alchemySecondaryLightYellow: "#FCDA51",
        alchemySecondaryBrightPurple: "#810997",
        alchemySecondaryChryslerBlue: "#5F00BA",
        alchemySecondaryLightOrange: "#FF9E1F",
        alchemySecondaryLightGrey: "#E1E1E1",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      fontFamily: {
        alchemy: ["Montserrat", "sans-serif"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        shimmerText: {
          "0%": { backgroundPosition: "-100% 0%" },
          "100%": { backgroundPosition: "100% 0%" },
        },
      },
      animation: {
        shimmerText: "shimmerText 2s linear infinite",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    plugin(function ({ addUtilities }) {
      addUtilities(
        // {
        //   ".scrollbar-always": {
        //     "scrollbar-width": "auto" /* Firefox */,
        //   },
        //   ".scrollbar-always::-webkit-scrollbar": {
        //     width: "8px",
        //   },
        //   ".scrollbar-always::-webkit-scrollbar-thumb": {
        //     "background-color": "#ccc",
        //   },
        // },
        {
          ".scrollbar-always": {
            "scrollbar-width": "auto", // Firefox: always show
            "overflow-y": "scroll", // Forces scrollbar space on all platforms
          },
          ".scrollbar-always::-webkit-scrollbar": {
            width: "8px",
          },
          ".scrollbar-always::-webkit-scrollbar-track": {
            // background: "#f0f0f0",
          },
          ".scrollbar-always::-webkit-scrollbar-thumb": {
            backgroundColor: "#a0a0a0",
            borderRadius: "6px",
            border: "1px solid #a0a0a0", // padding effect
          },
        },
        ["responsive"]
      );
    }),
  ],
};
