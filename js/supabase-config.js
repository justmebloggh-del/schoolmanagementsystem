/**
 * Supabase Configuration
 * School Management System
 * 
 * Replace the values below with your Supabase project credentials
 */

const SUPABASE_CONFIG = {
  // Your Supabase project URL
  // Get this from: Supabase Dashboard > Settings > API
  url: 'YOUR_SUPABASE_PROJECT_URL',
  
  // Anonymous key (public, for client-side use)
  // Get this from: Supabase Dashboard > Settings > API > Project API keys
  anonKey: 'YOUR_SUPABASE_ANON_KEY',
  
  // Database schema name (default is 'public')
  schema: 'public'
};

// Create Supabase client
const supabase = window.supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);

// Export for use in other modules
window.SUPABASE_CONFIG = SUPABASE_CONFIG;
window.supabaseClient = supabase;

