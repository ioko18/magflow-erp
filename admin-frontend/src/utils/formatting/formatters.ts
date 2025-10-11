/**
 * Common formatting utilities
 */

export const formatters = {
  /**
   * Format price with currency
   */
  formatPrice(price: number, currency: string = 'RON'): string {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: currency,
    }).format(price);
  },

  /**
   * Format number with thousands separator
   */
  formatNumber(num: number, decimals: number = 0): string {
    return new Intl.NumberFormat('ro-RO', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  },

  /**
   * Format date
   */
  formatDate(date: string | Date, format: 'short' | 'long' | 'full' = 'short'): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    
    const optionsMap: Record<string, Intl.DateTimeFormatOptions> = {
      short: { year: 'numeric' as const, month: '2-digit' as const, day: '2-digit' as const },
      long: { year: 'numeric' as const, month: 'long' as const, day: 'numeric' as const },
      full: { 
        year: 'numeric' as const, 
        month: 'long' as const, 
        day: 'numeric' as const,
        hour: '2-digit' as const,
        minute: '2-digit' as const
      },
    };

    return new Intl.DateTimeFormat('ro-RO', optionsMap[format]).format(d);
  },

  /**
   * Format relative time (e.g., "2 hours ago")
   */
  formatRelativeTime(date: string | Date): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'acum';
    if (diffMin < 60) return `acum ${diffMin} ${diffMin === 1 ? 'minut' : 'minute'}`;
    if (diffHour < 24) return `acum ${diffHour} ${diffHour === 1 ? 'oră' : 'ore'}`;
    if (diffDay < 7) return `acum ${diffDay} ${diffDay === 1 ? 'zi' : 'zile'}`;
    
    return formatters.formatDate(d, 'short');
  },

  /**
   * Format file size
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  },

  /**
   * Format percentage
   */
  formatPercentage(value: number, decimals: number = 1): string {
    return `${value.toFixed(decimals)}%`;
  },

  /**
   * Format phone number
   */
  formatPhone(phone: string): string {
    const cleaned = phone.replace(/\D/g, '');
    
    if (cleaned.length === 10) {
      return `${cleaned.slice(0, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7)}`;
    }
    
    return phone;
  },

  /**
   * Truncate text with ellipsis
   */
  truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
  },

  /**
   * Capitalize first letter
   */
  capitalize(text: string): string {
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
  },

  /**
   * Format status badge text
   */
  formatStatus(status: string): string {
    return status.split('_').map(formatters.capitalize).join(' ');
  },
};
