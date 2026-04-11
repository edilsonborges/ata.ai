import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4f46e5',
          dark: '#312e81',
          light: '#7c3aed',
        },
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #312e81, #4f46e5, #7c3aed)',
      },
    },
  },
  plugins: [],
};

export default config;
