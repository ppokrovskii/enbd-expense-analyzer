/**
 * 64-color palette for category visualization
 * 
 * Organized by hue families for intuitive color selection:
 * - Reds, Oranges, Yellows, Greens, Blues, Purples, Pinks, Neutrals
 */

export const COLOR_PALETTE = [
  // Reds (8 shades)
  '#FF6B6B', '#EE5A6F', '#E74C3C', '#C0392B',
  '#A93226', '#922B21', '#7B241C', '#641E16',
  
  // Oranges (8 shades)
  '#FF9F43', '#FF8C42', '#FF7043', '#F39C12',
  '#E67E22', '#D35400', '#BA4A00', '#A04000',
  
  // Yellows (8 shades)
  '#FFF176', '#FFEB3B', '#FDD835', '#FBC02D',
  '#F9A825', '#F57F17', '#F4D03F', '#F1C40F',
  
  // Greens (8 shades)
  '#A5D6A7', '#81C784', '#66BB6A', '#4CAF50',
  '#43A047', '#388E3C', '#2E7D32', '#1B5E20',
  
  // Teals & Cyans (8 shades)
  '#80DEEA', '#4DD0E1', '#26C6DA', '#00BCD4',
  '#00ACC1', '#0097A7', '#00838F', '#006064',
  
  // Blues (8 shades)
  '#90CAF9', '#64B5F6', '#42A5F5', '#2196F3',
  '#1E88E5', '#1976D2', '#1565C0', '#0D47A1',
  
  // Purples (8 shades)
  '#B39DDB', '#9575CD', '#7E57C2', '#673AB7',
  '#5E35B1', '#512DA8', '#4527A0', '#311B92',
  
  // Pinks & Magentas (8 shades)
  '#F48FB1', '#F06292', '#EC407A', '#E91E63',
  '#D81B60', '#C2185B', '#AD1457', '#880E4F',
] as const;

export type CategoryColor = typeof COLOR_PALETTE[number];

/**
 * Get a default color for a category based on its index
 */
export function getDefaultColor(index: number): CategoryColor {
  return COLOR_PALETTE[index % COLOR_PALETTE.length];
}

/**
 * Get color families for organized color picker
 */
export const COLOR_FAMILIES = {
  reds: COLOR_PALETTE.slice(0, 8),
  oranges: COLOR_PALETTE.slice(8, 16),
  yellows: COLOR_PALETTE.slice(16, 24),
  greens: COLOR_PALETTE.slice(24, 32),
  teals: COLOR_PALETTE.slice(32, 40),
  blues: COLOR_PALETTE.slice(40, 48),
  purples: COLOR_PALETTE.slice(48, 56),
  pinks: COLOR_PALETTE.slice(56, 64),
};

/**
 * Get a contrasting text color (black or white) for a given background color
 */
export function getContrastColor(backgroundColor: string): string {
  // Convert hex to RGB
  const hex = backgroundColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  
  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  
  // Return black for light colors, white for dark colors
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
}

