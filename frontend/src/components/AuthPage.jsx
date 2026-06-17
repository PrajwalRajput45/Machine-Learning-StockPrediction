import { SignIn, useSignUp } from '@clerk/clerk-react';
import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';

const validateEmailDomain = (email) => {
  if (!email || typeof email !== 'string') return { valid: false, error: 'Email is required' };

  const trimmed = email.trim().toLowerCase();
  if (trimmed.length === 0) return { valid: false, error: 'Email is required' };

  const atIndex = trimmed.indexOf('@');
  if (atIndex <= 0 || atIndex === trimmed.length - 1) {
    return { valid: false, error: 'Please enter a valid email address' };
  }

  const localPart = trimmed.substring(0, atIndex);
  if (localPart.includes(' ')) {
    return { valid: false, error: 'Please enter a valid email address' };
  }

  const domain = trimmed.substring(atIndex + 1);
  const dotIndex = domain.indexOf('.');

  if (domain === 'gmail.com') {
    return { valid: true };
  }

  if (domain.endsWith('.edu.in') && domain.length > 7) {
    return { valid: true };
  }

  return { valid: false, error: 'Only Gmail and educational (.edu.in) email addresses are allowed' };
};

const EmailInput = ({ value, onChange, onKeyDown, autoFocus }) => (
  <div className="space-y-1.5">
    <label className="block text-sm font-medium text-slate-300">Email address</label>
    <input
      type="email"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={onKeyDown}
      autoFocus={autoFocus}
      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors"
      placeholder="you@example.com"
    />
  </div>
);

const ValidationMessage = ({ error }) => (
  <motion.p
    initial={{ opacity: 0, y: -4 }}
    animate={{ opacity: 1, y: 0 }}
    className="mt-2 text-sm text-rose-400 flex items-center gap-1.5"
  >
    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    {error}
  </motion.p>
);

function CustomSignUp() {
  const { isLoaded, signUp } = useSignUp();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleEmailChange = useCallback((value) => {
    setEmail(value);
    if (error) setError('');
  }, [error]);

  const handleSubmit = useCallback(async (e) => {
    if (e) e.preventDefault();

    const validation = validateEmailDomain(email);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    if (!isLoaded || !signUp) return;

    setIsSubmitting(true);
    setError('');

    try {
      await signUp.create({ emailAddress: email.trim().toLowerCase() });
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
      setIsSubmitting(false);
    }
  }, [email, isLoaded, signUp]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <EmailInput
        value={email}
        onChange={handleEmailChange}
        onKeyDown={handleKeyDown}
        autoFocus
      />
      {error && <ValidationMessage error={error} />}
      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
            Creating account...
          </span>
        ) : (
          'Continue'
        )}
      </button>
    </form>
  );
}

export default function AuthPage({ type = 'sign-in' }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <svg width="48" height="48" viewBox="0 0 32 32" fill="none">
              <path
                d="M4 24L10 18L16 22L22 12L28 8"
                stroke="#10b981"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="28" cy="8" r="3" fill="#10b981" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">StockPredict AI</h1>
          <p className="text-slate-400">
            {type === 'sign-in' ? 'Welcome back!' : 'Create your account'}
          </p>
        </div>

        <div className="bg-slate-800/80 backdrop-blur rounded-xl p-6 border border-slate-700 shadow-xl">
          {type === 'sign-in' ? <SignIn /> : <CustomSignUp />}
        </div>
      </motion.div>
    </div>
  );
}