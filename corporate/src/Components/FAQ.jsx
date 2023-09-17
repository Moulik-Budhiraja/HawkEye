import Collapsible from './Collapsible';
export default function FAQ() {
	return (
		<div
			className='flex flex-col items-start justify-center w-full p-4'
			id='faq'
		>
			<Collapsible title='What do the glasses do?'>
				They help you see things that you normally wouldn&apos;t be able
				to see.
			</Collapsible>
			<Collapsible title='How do the glasses work?'>
				HawkEye uses a camera to capture the world around you, and then
				transforms it into something that can be processed. After this,
				Artificially Intelligent agents detect what is around you and
				send you back whatever you want to know about.
			</Collapsible>
			<Collapsible title='Why not just use a walking stick?'>
				A walking stick is cool. But it doesn&apos;t tell you if
				there&apos;s a spill ahead, or what the math problem on the
				board, 500 meters away, says.
			</Collapsible>
			<Collapsible title='How much is it?'>
				HawkEye is currently free to use!
			</Collapsible>

			<Collapsible title='What are some use cases?'>
				With the most advanced face recognition technology, HawkEye can
				help decrease stress in first encounters. Most people already
				forget names, but when someone is visually impaired, the
				situation becomes dire, HawkEye solves this.
			</Collapsible>
		</div>
	);
}
