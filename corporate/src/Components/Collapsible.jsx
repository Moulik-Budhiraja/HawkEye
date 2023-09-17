import { useState } from 'react';
import PropTypes from 'prop-types';
export default function Collapsible({ title, children }) {
	const [isOpen, setIsOpen] = useState(false);

	return (
		<div className='w-full px-5 pb-2 mx-auto rounded-md md:px-20'>
			<div
				onClick={() => setIsOpen(!isOpen)}
				className='flex items-center justify-between text-white bg-neutral-900 border-[0.1px] border-neutral-800 rounded-lg shadow cursor-pointer'
			>
				<h2 className='pl-3 text-xl font-medium text-white cursor-pointer md:text-2xl'>
					{title}
				</h2>
				<div className='p-5 transition duration-200 rounded'>
					<svg
						className={`w-5 h-5 ${
							isOpen && 'transform rotate-180'
						}`}
						fill='currentColor'
						viewBox='0 0 20 20'
						xmlns='http://www.w3.org/2000/svg'
					>
						<path
							fillRule='evenodd'
							d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z'
							clipRule='evenodd'
						/>
					</svg>
				</div>
			</div>
			{isOpen && (
				<div
					className={
						'pl-3 mt-2 text-xl text-white pb-7 display-effect' +
						isOpen
							? 'show'
							: ''
					}
				>
					{children}
				</div>
			)}
		</div>
	);
}

// props validation
Collapsible.propTypes = {
	title: PropTypes.string.isRequired,
	children: PropTypes.node.isRequired,
};
