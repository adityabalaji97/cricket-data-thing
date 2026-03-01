import React from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { A11y } from 'swiper/modules';
import { Box } from '@mui/material';
import 'swiper/css';

const VenueCarousel = ({ cards, onSlideChange, swiperRef }) => (
  <Box sx={{
    height: '100%',
    '.swiper': {
      height: '100%',
    },
    '.swiper-slide': {
      height: 'auto',
      display: 'flex',
      alignItems: 'stretch',
    },
  }}>
    <Swiper
      modules={[A11y]}
      onSwiper={(swiper) => { swiperRef.current = swiper; }}
      onSlideChange={(swiper) => onSlideChange(swiper.activeIndex)}
      spaceBetween={8}
      slidesPerView={1}
      speed={300}
      touchEventsTarget="wrapper"
      touchStartPreventDefault={false}
      threshold={14}
      touchAngle={30}
      resistanceRatio={0.6}
      noSwiping
      noSwipingSelector=".MuiTabs-root, .MuiTableContainer-root, .MuiPagination-root, .MuiButtonBase-root, [data-carousel-no-swipe]"
      observer
      observeParents
      style={{ height: '100%' }}
    >
      {cards.map((card) => (
        <SwiperSlide key={card.id}>
          <Box sx={{ width: '100%', px: 0, py: 0.5, display: 'flex' }}>
            {card.content}
          </Box>
        </SwiperSlide>
      ))}
    </Swiper>
  </Box>
);

export default VenueCarousel;
