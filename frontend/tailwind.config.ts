import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#007AFF',
          'blue-hover': '#0051D5',
          green: '#34C759',
          red: '#FF3B30',
          orange: '#FF9500',
          gray: {
            1: '#F2F2F7',
            2: '#E5E5EA',
            3: '#D1D1D6',
            4: '#C7C7CC',
            5: '#AEAEB2',
            6: '#8E8E93',
          }
        }
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      fontSize: {
        'title': ['2.125rem', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '700' }],
        'heading': ['1.25rem', { lineHeight: '1.4', letterSpacing: '-0.01em', fontWeight: '600' }],
        'body': ['0.9375rem', { lineHeight: '1.5' }],
        'caption': ['0.8125rem', { lineHeight: '1.4' }],
        'label': ['0.75rem', { lineHeight: '1.3', fontWeight: '500' }],
      },
      boxShadow: {
        'apple-sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'apple-md': '0 4px 6px rgba(0, 0, 0, 0.07)',
        'apple-lg': '0 10px 15px rgba(0, 0, 0, 0.1)',
        'apple-xl': '0 20px 25px rgba(0, 0, 0, 0.1)',
      },
      borderRadius: {
        'apple-sm': '0.375rem',
        'apple-md': '0.5rem',
        'apple-lg': '0.75rem',
        'apple-xl': '1rem',
      },
      transitionDuration: {
        'apple-fast': '150ms',
        'apple-base': '200ms',
        'apple-slow': '300ms',
      },
      transitionTimingFunction: {
        'apple': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      maxWidth: {
        'container': '1280px',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
export default config;


