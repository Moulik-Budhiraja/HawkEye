export default function Navbar() {
	return (
		<div className='flex flex-row items-center justify-between w-full'>
			<a href='/'>
				<div className='flex flex-row gap-3 flex-start'>
					<p className='text-3xl font-bold align-middle'>HawkEye</p>
				</div>
			</a>
			<a
				href='/login'
				className='hidden p-5 text-lg font-semibold rounded-lg cursor-pointer md:block'
			>
				Visit Dashboard
			</a>
		</div>
	);
}
