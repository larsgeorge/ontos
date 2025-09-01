import React from 'react';
import { cn } from '@/lib/utils'; // Assuming you have clsx/tailwind-merge utility

interface RelativeDateProps {
  date: Date | string | number | null | undefined;
  className?: string;
}

// Helper function to zero out time component of a Date
const getDateOnly = (date: Date): Date => {
  const newDate = new Date(date);
  newDate.setHours(0, 0, 0, 0);
  return newDate;
};

export const RelativeDate: React.FC<RelativeDateProps> = ({ date, className }) => {
  if (!date) {
    return <span className={cn(className)} title="No date provided">N/A</span>;
  }

  let dateObj: Date;
  try {
    dateObj = new Date(date);
    // Check if date is valid after parsing
    if (isNaN(dateObj.getTime())) {
      throw new Error('Invalid Date');
    }
  } catch (error) {
    console.error("Error parsing date:", date, error);
    return <span className={cn(className)} title={`Invalid date: ${date}`}>Invalid Date</span>;
  }

  const now = new Date();
  const today = getDateOnly(now);
  const inputDateOnly = getDateOnly(dateObj);

  const timeDiff = today.getTime() - inputDateOnly.getTime();
  const daysDiff = Math.round(timeDiff / (1000 * 60 * 60 * 24)); // Difference in days

  let displayString: string;

  if (daysDiff < 0) {
    // Handle dates in the future (show locale date)
    displayString = dateObj.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric'
    });
  } else if (daysDiff === 0) {
    displayString = 'Today';
  } else if (daysDiff > 0 && daysDiff <= 7) {
    displayString = `${daysDiff} day${daysDiff > 1 ? 's' : ''} ago`;
  } else {
    // Use locale-specific date format for older dates
    displayString = dateObj.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric'
    });
  }

  // Full date and time for the tooltip
  const tooltipString = dateObj.toLocaleString();

  return (
    <span className={cn(className)} title={tooltipString}>
      {displayString}
    </span>
  );
};