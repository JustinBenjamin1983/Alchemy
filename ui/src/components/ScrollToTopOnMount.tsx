import { useLayoutEffect } from "react";

export default function ScrollToTopOnMount({
  target = null,
  forceRerenderOn = [],
}) {
  useLayoutEffect(() => {
    try {
      window.scrollTo({
        top: target?.current?.offsetTop || 0,
        behavior: "smooth",
      });
    } catch (e) {
      // Do nothing
    }
  }, forceRerenderOn);

  return null;
}
