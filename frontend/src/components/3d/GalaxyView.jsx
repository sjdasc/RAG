// src/components/3d/GalaxyView.jsx
import React, {
  // useMemo,
  useRef,
  useState,
  useEffect,
} from "react";
import {
  Canvas,
  useFrame, // useFrame 추가
} from "@react-three/fiber";
import {
  OrbitControls,
  Stars,
  Html,
  Line,
} from "@react-three/drei";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "../../stores/useChatStore"; // Store import
import "../../styles/GalaxyView.css";

// 개별 별(데이터 포인트) 컴포넌트
const StarNode = ({
  position,
  color,
  label,
  isQuery,
  url,
  page,
}) => {
  const ref = useRef();
  const [hovered, setHover] = useState(false);

  // 쿼리 노드는 반짝이는 효과 추가
  useFrame((state) => {
    if (isQuery && ref.current) {
      const scale =
        1 +
        Math.sin(state.clock.elapsedTime * 3) *
          0.2;
      ref.current.scale.set(scale, scale, scale);
    }
  });

  const handleClick = (e) => {
    e.stopPropagation();
    if (url) {
      window.open(url, "_blank");
    }
  };

  return (
    <mesh
      ref={ref}
      position={position}
      scale={hovered ? 1.8 : isQuery ? 1.5 : 1}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHover(true);
        document.body.style.cursor = url
          ? "pointer"
          : "default";
      }}
      onPointerOut={() => {
        setHover(false);

        document.body.style.cursor = "default";
      }}
      onClick={handleClick}
    >
      <sphereGeometry args={[0.15, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={
          hovered || isQuery ? 2 : 0.5
        }
        roughness={0.2}
      />
      {hovered && (
        <Html distanceFactor={10}>
          <div className="galaxy-tooltip">
            <div className="galaxy-tooltip-title">
              {label}
            </div>
            {!isQuery && page && (
              <div className="galaxy-tooltip-page">
                Page: {page}
              </div>
            )}
            {url && (
              <div className="galaxy-tooltip-hint">
                (Click to open)
              </div>
            )}
          </div>
        </Html>
      )}
    </mesh>
  );
};

const GalaxyView = () => {
  const navigate = useNavigate();
  const { currentChatId, currentResult } =
    useChatStore(); // Store에서 데이터 가져오기
  const [dataPoints, setDataPoints] = useState(
    []
  );

  // 백엔드에서 실제 벡터 데이터 가져오기
  useEffect(() => {
    const fetchData = async () => {
      if (!currentChatId) return;

      // 검색 결과가 없으면 전체 데이터 시각화 (기존 로직)
      try {
        // 쿼리가 있으면 파라미터에 추가
        const queryParam = currentResult?.query
          ? `&query=${encodeURIComponent(
              currentResult.query
            )}`
          : "";

        const response = await fetch(
          `/api/galaxy?session_id=${currentChatId}${queryParam}`
        );

        if (response.ok) {
          const data = await response.json();
          setDataPoints(data);
        }
      } catch (error) {
        console.error(
          "Failed to fetch galaxy data:",
          error
        );
      }
    };
    fetchData();
  }, [currentChatId, currentResult]); // 의존성 배열 업데이트

  return (
    <div className="galaxy-container">
      <button
        onClick={() => navigate(-1)}
        className="galaxy-back-btn"
      >
        ← Back to Home
      </button>

      <div className="galaxy-legend-container">
        <div className="galaxy-legend-title">
          Knowledge Galaxy View
        </div>
        <div className="galaxy-legend-list">
          <div className="galaxy-legend-item">
            <span className="w-3 h-3 rounded-full bg-[#FDE047]"></span>
            <span>Question (질문)</span>
          </div>
          <div className="galaxy-legend-item">
            <span className="w-3 h-3 rounded-full bg-[#F43F5E]"></span>
            <span>PDF Document</span>
          </div>
          <div className="galaxy-legend-item">
            <span className="w-3 h-3 rounded-full bg-[#06B6D4]"></span>
            <span>TXT / MD File</span>
          </div>
          <div className="galaxy-legend-item">
            <span className="w-3 h-3 rounded-full bg-[#F97316]"></span>
            <span>PPT / PPTX Slide</span>
          </div>
          <div className="galaxy-legend-item">
            <span className="w-3 h-3 rounded-full bg-[#8B5CF6]"></span>
            <span>Other Files</span>
          </div>
        </div>
      </div>

      <Canvas
        camera={{ position: [0, 0, 20], fov: 60 }}
      >
        <color
          attach="background"
          args={["#000000"]}
        />
        <ambientLight intensity={0.3} />
        <pointLight
          position={[10, 10, 10]}
          intensity={1.5}
          color="#ffffff"
        />
        <pointLight
          position={[-10, -10, -10]}
          intensity={1.5}
          color="#ffffff"
        />

        <Stars
          radius={100}
          depth={50}
          count={5000}
          factor={4}
          saturation={0}
          fade
          speed={0}
        />

        {/* 실제 데이터 렌더링 */}
        <group rotation={[0, Math.PI / 4, 0]}>
          {dataPoints.map((point) => (
            <StarNode
              key={point.id}
              position={point.position}
              color={point.color}
              label={point.label}
              isQuery={point.isQuery}
              url={point.url}
              page={point.page}
            />
          ))}

          {/* 질문 벡터와 중심점 연결선 */}
          {dataPoints.map((point) => {
            if (point.isQuery) {
              return (
                <Line
                  key={`line-${point.id}`}
                  points={[
                    [0, 0, 0],
                    point.position,
                  ]}
                  color="white"
                  lineWidth={1.5}
                  dashed={true}
                  dashScale={2}
                  dashSize={0.5}
                  gapSize={0.5}
                  opacity={0.6}
                  transparent
                />
              );
            }
            return null;
          })}

          {/* 중심점 가이드 (투명한 구) */}
          <mesh position={[0, 0, 0]}>
            <sphereGeometry
              args={[0.2, 16, 16]}
            />
            <meshBasicMaterial
              color="white"
              transparent
              opacity={0.3}
              wireframe
            />
          </mesh>
        </group>

        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          autoRotate={true}
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
};

export default GalaxyView;
