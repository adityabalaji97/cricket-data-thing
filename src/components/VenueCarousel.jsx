import React from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Pagination, A11y } from 'swiper/modules';
import { Box } from '@mui/material';
import 'swiper/css';
import 'swiper/css/pagination';

const VenueCarousel = ({ slides, onSlideChange, swiperRef }) => (
  <Box sx={{
    '.swiper-slide': {
      overflowY: 'auto',
      maxHeight: 'calc(100vh - 160px)',
      WebkitOverflowScrolling: 'touch',
    },
    '.swiper-pagination': {
      display: 'none',
    },
  }}>
    <Swiper
      modules={[Pagination, A11y]}
      onSwiper={(swiper) => { swiperRef.current = swiper; }}
      onSlideChange={(swiper) => onSlideChange(swiper.activeIndex)}
      spaceBetween={16}
      slidesPerView={1}
      speed={300}
      touchEventsTarget="wrapper"
      touchStartPreventDefault={false}
      style={{ minHeight: '60vh' }}
    >
      {slides.map((slide) => (
        <SwiperSlide key={slide.id}>
          <Box sx={{ px: { xs: 0.5, sm: 1 }, py: 1 }}>
            {slide.content}
          </Box>
        </SwiperSlide>
      ))}
    </Swiper>
  </Box>
);

export default VenueCarousel;
