
SRCS = $(wildcard src/*.c)
BUILD_DIR = build
OBJS = $(SRCS:.c=.o)

all: $(OBJS) ${BUILD_DIR}/
	$(CC) -o ${BUILD_DIR}/easyperf $(OBJS) -Iinclude -Wall -Wextra -Werror -g -O2
	rm -f $(OBJS)

%.o: %.c
	$(CC) -c $< -o $@ -Iinclude -Wall -Wextra -Werror -g -O2

%/:
	mkdir -p $@