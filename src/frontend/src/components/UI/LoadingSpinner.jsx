import { motion } from 'framer-motion'
import React from 'react'

const LoadingSpinner = ({
    size = 'medium',
    color = 'primary',
    text = null,
    className = ''
}) => {
    const sizeClasses = {
        small: 'w-4 h-4',
        medium: 'w-8 h-8',
        large: 'w-12 h-12',
        xlarge: 'w-16 h-16'
    }

    const colorClasses = {
        primary: 'text-primary-600',
        white: 'text-white',
        gray: 'text-gray-600',
        success: 'text-success-600',
        warning: 'text-warning-600',
        danger: 'text-danger-600'
    }

    return (
        <div className={`flex items-center justify-center ${className}`}>
            <div className="flex flex-col items-center space-y-2">
                <motion.div
                    className={`${sizeClasses[size]} ${colorClasses[color]} relative`}
                    animate={{ rotate: 360 }}
                    transition={{
                        duration: 1,
                        repeat: Infinity,
                        ease: "linear"
                    }}
                >
                    <svg
                        className="w-full h-full"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <circle
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeDasharray="60 40"
                            fill="none"
                            className="opacity-25"
                        />
                        <circle
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeDasharray="15 85"
                            fill="none"
                            transform="rotate(-90 12 12)"
                        />
                    </svg>
                </motion.div>

                {text && (
                    <motion.p
                        className={`text-sm font-medium ${colorClasses[color]} opacity-75`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        {text}
                    </motion.p>
                )}
            </div>
        </div>
    )
}

export default LoadingSpinner 