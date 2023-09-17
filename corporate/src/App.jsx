import {
	EffectFade,
	Scrollbar,
	A11y,
	Mousewheel,
	Parallax,
} from 'swiper/modules';
import { Swiper, SwiperSlide } from 'swiper/react';
import Cards from './Components/Cards';
import FAQ from './Components/FAQ';
import Hero from './Components/Hero';
import Navbar from './Components/Navbar';
import 'swiper/css';
import 'swiper/css/scrollbar';
import 'swiper/css/mousewheel';

const FirstSlide = () => {
	return (
		<div data-swiper-parallax='-3500'>
			<Navbar />
			<div className='flex flex-col items-center h-full p-10'>
				<Hero data-swiper-parallax='-4000' />
			</div>
		</div>
	);
};

const SecondSlide = () => {
	return (
		<div
			className='flex flex-col justify-around h-full'
			data-swiper-parallax='-4300'
		>
			<h1
				className='p-0 m-0 text-6xl font-extrabold text-center h-fit'
				data-swiper-parallax='-4000'
			>
				Glasses that defy limits{' '}
			</h1>
			<Cards />
		</div>
	);
};

const ThirdSlide = () => {
	return (
		<div
			className='flex flex-wrap justify-center h-full gap-8'
			data-swiper-parallax='-3000'
		>
			<h1
				className='mt-[1em] md:mt-[0.25em] font-extrabold text-center text-5xl lg:text-6xl'
				data-swiper-parallax='-4000'
			>
				Built for Everyone{' '}
			</h1>
			<FAQ />
		</div>
	);
};

const data = [
	<FirstSlide key={1} />,
	<SecondSlide key={2} />,
	<ThirdSlide key={3} />,
];

function App() {
	return (
		<Swiper
			direction='vertical'
			slidesPerView={1}
			style={{
				display: 'flex',
				flexDirection: 'column',
				width: '100%',
				height: '100%',
				margin: 0,
				gap: '0em',
			}}
			modules={[Scrollbar, Mousewheel, Parallax]}
			parallax={true}
			speed={1000} // Adjust the speed of the parallax effect
			scrollbar={{
				draggable: true,
				hide: true,
				snapOnRelease: true,
				verticalClass: 'swiper-scrollbar',
			}}
			mousewheel={{
				forceToAxis: true,
				releaseOnEdges: true,
				sensitivity: 1,
				eventsTarged: 'container',
			}}
		>
			{data.map((item, index) => (
				<SwiperSlide
					className='w-full h-full pt-8 pl-12 pr-12 bg-black bg-center bg-cover bg-nature-1'
					key={index}
				>
					{item}
				</SwiperSlide>
			))}
		</Swiper>
	);
}

export default App;
