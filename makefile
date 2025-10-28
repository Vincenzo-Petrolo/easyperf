
SRCS = $(wildcard src/*.c)
BUILD_DIR = build
OBJS = $(SRCS:.c=.o)

easyperf: $(OBJS) ${BUILD_DIR}/
	$(CC) -o $@ $(OBJS) -Iinclude -g -O2
	rm -f $(OBJS)


%.o: %.c
	$(CC) -c $< -o $@ -Iinclude -g -O2

%/:
	mkdir -p $@