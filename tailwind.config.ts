import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forest: '#1E3A32',
        forestDeep: '#132722',
        ivory: '#FBF9F4',
        parchment: '#FFFDF8',
        gold: '#A8823C',
        sage: '#7E9B8B',
        ink: '#22201C',
        muted: '#6B6862',
        canvas: '#FBF9F4'
      },
      boxShadow: {
        soft: '0 12px 40px rgba(19, 39, 34, 0.08)',
        lift: '0 20px 60px rgba(19, 39, 34, 0.14)'
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.25rem'
      }
    }
  },
  plugins: []
};

export default config;
