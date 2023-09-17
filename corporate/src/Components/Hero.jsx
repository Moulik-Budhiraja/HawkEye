import Glasses from './glasses.png';
export default function Hero() {
	return (
		<div className='flex flex-col min-h-[75vh] w-5/6 justify-between align-middle text-center items-center py-5'>
			<div className='flex flex-col items-center rounded-xl'>
				<img
					src={Glasses}
					width={800}
					height={200}
					alt='Glasses'
					className='animate-move-and-enlarge'
				/>
			</div>
			<div className='flex flex-col items-center justify-center gap-y-5'>
				<h1 className='font-mono text-xl'>The HawkEye 15</h1>
				<button className='px-5 py-3 bg-blue-800 rounded-full w-fit'>
					<p>Order Now</p>
				</button>
			</div>
		</div>
	);
}
