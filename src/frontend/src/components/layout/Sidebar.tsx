import {
    ArrowTrendingUpIcon,
    ChartBarIcon,
    ChartPieIcon,
    CogIcon,
    KeyIcon,
    ServerIcon,
    ShieldCheckIcon,
    UsersIcon
} from '@heroicons/react/24/outline';
import { NavLink } from 'react-router-dom';

const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: ChartBarIcon },
    { name: 'Live Indices', href: '/indices', icon: ArrowTrendingUpIcon },
    { name: 'User Management', href: '/users', icon: UsersIcon },
    { name: 'User Analytics', href: '/analytics', icon: ChartPieIcon },
    { name: 'Trading Control', href: '/trading', icon: CogIcon },
    { name: 'Daily Auth Tokens', href: '/auth-tokens', icon: KeyIcon },
    { name: 'System Health', href: '/system', icon: ServerIcon },
];

export default function Sidebar() {
    return (
        <div className="hidden md:flex md:w-64 md:flex-col">
            <div className="flex flex-col flex-grow pt-5 overflow-y-auto bg-gray-900">
                <div className="flex items-center flex-shrink-0 px-4">
                    <div className="flex items-center">
                        <ShieldCheckIcon className="h-8 w-8 text-blue-500" />
                        <span className="ml-2 text-xl font-bold text-white">ShareKhan Pro</span>
                    </div>
                </div>
                <div className="mt-8 flex-grow flex flex-col">
                    <nav className="flex-1 px-2 pb-4 space-y-1">
                        {navigation.map((item) => (
                            <NavLink
                                key={item.name}
                                to={item.href}
                                className={({ isActive }) =>
                                    `group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${isActive
                                        ? 'bg-gray-800 text-white'
                                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                                    }`
                                }
                            >
                                <item.icon className="mr-3 h-6 w-6 flex-shrink-0" aria-hidden="true" />
                                {item.name}
                            </NavLink>
                        ))}
                    </nav>
                </div>
                <div className="flex-shrink-0 flex border-t border-gray-700 p-4">
                    <div className="flex items-center">
                        <div className="ml-3">
                            <p className="text-sm font-medium text-white">ShareKhan System</p>
                            <p className="text-xs font-medium text-gray-400">v2.0.0 Production</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
} 