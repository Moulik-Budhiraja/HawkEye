// four cards that talk about what HawkEye does for visually impaired people
import { Swiper, SwiperSlide } from 'swiper/react';
import { EffectCards, Mousewheel, Navigation, Scrollbar } from 'swiper/modules';

import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/effect-cards';
import 'swiper/css/scrollbar';
import 'swiper/css/mousewheel';

const cardList = [
	{
		title: 'For the Visually Impaired',
		description:
			'Helps visually impaired people to navigate through the world with ease and provides them a sense of independence.',
	},
	{
		title: 'Cutting the Edge',
		description:
			'Uses the latest technology and best models to provide a real time experience to users.',
	},
	{
		title: 'Changing the World',
		description:
			'With no learning curve, it changes the way people with impaired vision see the world.',
	},
	{
		title: 'Correcting the World',
		description:
			'Providing a remedy for people with cataracts, glycoma and visual impairments to correct their sense of the world.',
	},
];
export default function Cards() {
	return (
		<Swiper
			direction='horizontal'
			style={{
				display: 'flex',
				flexDirection: 'row',
				width: '50%',
				margin: 0,
				gap: '0em',
				alignSelf: 'center',
			}}
			slidesPerView={1}
			modules={[Navigation, EffectCards, Scrollbar, Mousewheel]}
			navigation={{
				enabled: true,
				nextEl: '.swiper-button-next',
				prevEl: '.swiper-button-prev',
			}}
			mousewheel={{
				forceToAxis: true,
				releaseOnEdges: true,
				sensitivity: 1,
				eventsTarged: 'container',
			}}
			scrollbar={{
				draggable: true,
				hide: true,
				snapOnRelease: true,
			}}
			effect='cards'
		>
			<div className='swiper-button-prev'></div>
			{cardList.map((card) => {
				return (
					<SwiperSlide
						key={card.title}
						className='flex flex-col items-center justify-center gap-5 p-10 shadow-md rounded-2xl bg-neutral-700 bg-hovers'
					>
						<h2 className='text-2xl font-bold text-center'>
							{card.title}
						</h2>
						<p className='max-w-lg text-lg text-center'>
							{card.description}
						</p>
					</SwiperSlide>
				);
			})}
			<div className='swiper-button-next'></div>
		</Swiper>
	);
}
